from pathlib import Path

import cv2
import numpy as np
from PIL import Image


def _rgb_array(img):
    if not isinstance(img, Image.Image):
        raise TypeError("img must be a PIL.Image.Image")
    return np.asarray(img.convert("RGB"))


def _pil_rgb(array):
    return Image.fromarray(np.clip(array, 0, 255).astype(np.uint8), mode="RGB")


def gray_world_white_balance(img):
    """Apply gray-world white balance and return an RGB PIL image."""
    rgb = _rgb_array(img).astype(np.float32)
    channel_means = rgb.mean(axis=(0, 1))
    target_mean = float(channel_means.mean())
    scales = target_mean / np.maximum(channel_means, 1.0)
    return _pil_rgb(rgb * scales)


def clahe_luminance(img):
    """Apply CLAHE to the LAB lightness channel without changing chroma."""
    rgb = _rgb_array(img)
    lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    lab[:, :, 0] = clahe.apply(lab[:, :, 0])
    return _pil_rgb(cv2.cvtColor(lab, cv2.COLOR_LAB2RGB))


def bilateral_denoise(img):
    """Reduce image noise while preserving edges."""
    rgb = _rgb_array(img)
    return _pil_rgb(cv2.bilateralFilter(rgb, 9, 75, 75))


def unsharp_mask(img):
    """Sharpen an image with an unsharp mask."""
    rgb = _rgb_array(img)
    blurred = cv2.GaussianBlur(rgb, (0, 0), sigmaX=1.0)
    sharpened = cv2.addWeighted(rgb, 1.5, blurred, -0.5, 0)
    return _pil_rgb(sharpened)


def lanczos_resize(img, size):
    """Resize to a square integer size or an explicit (width, height) pair."""
    rgb = _rgb_array(img)
    if isinstance(size, int):
        width, height = size, size
    else:
        try:
            width, height = size
        except (TypeError, ValueError) as error:
            raise ValueError("size must be an integer or (width, height)") from error
    if width <= 0 or height <= 0:
        raise ValueError("resize dimensions must be positive")
    resized = cv2.resize(rgb, (int(width), int(height)), interpolation=cv2.INTER_LANCZOS4)
    return _pil_rgb(resized)


def edge_map(img):
    """Return a PIL grayscale image containing Canny edges."""
    rgb = _rgb_array(img)
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    edges = cv2.Canny(gray, threshold1=100, threshold2=200)
    return Image.fromarray(edges, mode="L")


def quality_report(img):
    """Measure sharpness, luminance contrast, colorfulness, clipping, and diagnostics."""
    rgb = _rgb_array(img)
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    gray_float = gray.astype(np.float32)
    lab_lightness = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB)[:, :, 0]
    channel_means = rgb.astype(np.float32).mean(axis=(0, 1))
    mean_luminance = float(gray_float.mean())
    median_filtered = cv2.medianBlur(gray, 3)
    residual = gray.astype(np.float32) - median_filtered.astype(np.float32)
    noise_estimate = float(np.median(np.abs(residual)) / 0.6745)

    red, green, blue = (rgb[:, :, index].astype(np.float32) for index in range(3))
    rg = np.abs(red - green)
    yb = np.abs(0.5 * (red + green) - blue)
    colorfulness = float(
        np.sqrt(rg.std() ** 2 + yb.std() ** 2)
        + 0.3 * np.sqrt(rg.mean() ** 2 + yb.mean() ** 2)
    )

    channel_mean = max(float(channel_means.mean()), 1.0)
    channel_imbalance = float(
        (channel_means.max() - channel_means.min()) / channel_mean * 100.0
    )
    clipped_pixels = np.any((rgb <= 1) | (rgb >= 254), axis=2)

    return {
        "sharpness": float(cv2.Laplacian(gray, cv2.CV_64F).var()),
        "contrast": float(lab_lightness.std()),
        "colorfulness": colorfulness,
        "clipped_pixel_ratio": float(clipped_pixels.mean()),
        "channel_imbalance": channel_imbalance,
        "noise_estimate": noise_estimate,
        "mean_luminance": mean_luminance,
    }


def detect_artifacts(img):
    """Return image artifact flags, including an FFT high-frequency check."""
    rgb = _rgb_array(img)
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    gray_float = gray.astype(np.float32)
    gray_std = float(gray_float.std())

    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    saturation = hsv[:, :, 1]
    high_saturation_ratio = float((saturation >= 245).mean())
    overexposed_ratio = float((gray >= 250).mean())
    underexposed_ratio = float((gray <= 5).mean())

    centered = gray_float - gray_float.mean()
    spectrum = np.fft.fftshift(np.fft.fft2(centered))
    power = np.abs(spectrum) ** 2
    height, width = gray.shape
    y = np.linspace(-0.5, 0.5, height, endpoint=False)
    x = np.linspace(-0.5, 0.5, width, endpoint=False)
    xx, yy = np.meshgrid(x, y)
    high_frequency = np.hypot(xx, yy) >= 0.35
    total_power = float(power.sum())
    high_frequency_ratio = (
        float(power[high_frequency].sum() / total_power) if total_power else 0.0
    )

    return {
        "blank_or_black": gray_std < 5.0,
        "oversaturated": high_saturation_ratio > 0.25,
        "overexposed": overexposed_ratio > 0.10,
        "underexposed": underexposed_ratio > 0.10,
        "checkerboard": high_frequency_ratio > 0.35,
        "high_saturation_ratio": high_saturation_ratio,
        "overexposed_pixel_ratio": overexposed_ratio,
        "underexposed_pixel_ratio": underexposed_ratio,
        "high_frequency_ratio": high_frequency_ratio,
    }


def run_pipeline(img, target_size=None, adaptive=True, wb_strength=0.3):
    """Enhance an image and return it with named intermediates and quality reports."""
    current = img.convert("RGB")
    before_report = quality_report(current)
    intermediates = []

    def apply_step(name, operation):
        nonlocal current
        current = operation(current)
        intermediates.append((name, current.copy()))

    if before_report["channel_imbalance"] > 40.0:
        balanced = _rgb_array(gray_world_white_balance(current))
        original = _rgb_array(current)
        blended = cv2.addWeighted(
            original,
            1.0 - wb_strength,
            balanced,
            wb_strength,
            0,
        )
        current = _pil_rgb(blended)
        intermediates.append(("gray_world_white_balance", current.copy()))

    report = quality_report(current)
    if not adaptive or report["contrast"] < 40.0:
        apply_step("clahe_luminance", clahe_luminance)

    report = quality_report(current)
    if not adaptive or report["noise_estimate"] > 8.0:
        apply_step("bilateral_denoise", bilateral_denoise)

    report = quality_report(current)
    if not adaptive or report["sharpness"] < 100.0:
        apply_step("unsharp_mask", unsharp_mask)

    if target_size is not None:
        if isinstance(target_size, int):
            target_dimensions = (target_size, target_size)
        else:
            target_dimensions = tuple(target_size)
        if current.size != target_dimensions:
            apply_step(
                "lanczos_resize",
                lambda image: lanczos_resize(image, target_size),
            )

    intermediates.append(("edge_map", edge_map(current)))
    after_report = quality_report(current)
    return current, intermediates, before_report, after_report


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parent.parent
    input_path = project_root / "outputs" / "test_fast.png"
    if not input_path.is_file():
        raise FileNotFoundError(f"Demo input image not found: {input_path}")

    output_dir = project_root / "outputs" / "postprocess_demo"
    output_dir.mkdir(parents=True, exist_ok=True)
    with Image.open(input_path) as source:
        final_image, steps, before, after = run_pipeline(source, target_size=512)

    for index, (step_name, intermediate) in enumerate(steps, start=1):
        intermediate.save(output_dir / f"{index:02d}_{step_name}.png")
    final_image.save(output_dir / "final.png")
    print(f"Before: {before}")
    print(f"After: {after}")
