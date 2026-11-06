import inspect
import os
import re

import gradio as gr

from src.adaptive import TIERS, generate_with_fallback
from src.ui_theme import CSS, HEAD, HERO_HTML, make_theme, side_gallery_html


EXAMPLE_PROMPTS = [
    "a red cube to the left of a blue sphere on a white table",
    "three yellow pears beside two green apples in a wooden bowl",
    "four small orange balls arranged around one large purple cube",
    "a black cat sitting between a brown dog and a white chair",
]


def generate(prompt, tier_label, postprocess, enhance, candidate_count, seed):
    if not prompt or not prompt.strip():
        gr.Warning("Please enter a prompt before generating.")
        return None, None, "", [], [], {}, {}
    if not re.search(r"[A-Za-z0-9]", prompt):
        gr.Warning("Please enter a descriptive prompt.")
        return None, None, "", [], [], {}, {}

    tier = "auto" if tier_label == "Auto" else tier_label
    num_candidates = "auto" if candidate_count == "Auto" else int(candidate_count)
    try:
        result = generate_with_fallback(
            prompt=prompt,
            tier=tier,
            seed=int(seed),
            postprocess=postprocess,
            enhance=enhance,
            num_candidates=num_candidates,
        )
    except ValueError as error:
        gr.Warning(str(error))
        return None, None, "", [], [], {}, {}
    except Exception as error:
        raise gr.Error(f"Image generation failed: {error}") from error

    tier_settings = TIERS[result["tier_used"]]
    model_config = result.get("config", tier_settings["config"])
    steps = result.get("steps", tier_settings["steps"])
    resolution = result.get(
        "resolution",
        result.get("size", tier_settings["size"]),
    )
    if isinstance(resolution, (tuple, list)):
        resolution = "×".join(str(dimension) for dimension in resolution)
    elif isinstance(resolution, int):
        resolution = f"{resolution}×{resolution}"

    if model_config == "fast":
        optimizations = f"fp16 + LCM-LoRA, {steps} steps"
    elif model_config == "tiny":
        optimizations = "fp16 + BK-SDM-Tiny + Lanczos upscale"
    elif model_config == "fp16":
        optimizations = "fp16, 25 steps"
    else:
        optimizations = "none (fp32 reference)"

    info = (
        f"**Tier used:** {result['tier_used']}  \n"
        f"**Reason:** {result['reason']}  \n"
        f"**Fallback:** {'Yes' if result['fallback_happened'] else 'No'}  \n"
        f"**Artifact retry:** {'Yes' if result.get('artifact_retry') else 'No'}  \n"
        f"**Model config:** {model_config}  \n"
        f"**Steps:** {steps}  \n"
        f"**Resolution:** {resolution}  \n"
        f"**Optimizations:** {optimizations}  \n"
        f"**Enhanced prompt:** {result['enhanced_prompt']}  \n"
        f"**Generation latency:** {result['latency_s']:.2f} s  \n"
        f"**Load time:** {result['load_time_s']:.2f} s  \n"
        f"**Peak memory:** {result['peak_mem_mb']:.1f} MB"
    )
    gallery = [
        (image, step_name)
        for step_name, image in result["intermediates"]
    ]
    candidate_gallery = [
        (
            image,
            f"CLIP {score:.2f}"
            + (" — Chosen" if index == result["chosen_index"] else ""),
        )
        for index, (image, score) in enumerate(
            zip(result["candidates"], result["candidate_scores"])
        )
    ]
    quality = {
        "quality_before": result["quality_before"],
        "quality_after": result["quality_after"],
        "artifacts": result["artifacts"],
    }
    controller_decisions = {
        "prompt_analysis": result["prompt_analysis"],
        "resources": result["resources"],
    }
    return (
        result["raw_image"],
        result["final_image"],
        info,
        gallery,
        candidate_gallery,
        quality,
        controller_decisions,
    )


theme_options = {"css": CSS, "head": HEAD, "theme": make_theme()}
launch_supports_css = "css" in inspect.signature(gr.Blocks.launch).parameters
with gr.Blocks(
    title="Flicker",
    **({} if launch_supports_css else theme_options),
) as demo:
    with gr.Row(equal_height=False, elem_id="flicker-shell"):
        with gr.Column(scale=1, min_width=180):
            gr.HTML(side_gallery_html("left"))

        with gr.Column(scale=4):
            gr.HTML(HERO_HTML)
            with gr.Row(equal_height=False):
                with gr.Column(scale=2):
                    prompt = gr.Textbox(
                        label="Prompt",
                        placeholder="Describe the image you want to create...",
                        lines=4,
                    )
                    generate_button = gr.Button(
                        "Generate",
                        variant="primary",
                        elem_id="flicker-generate",
                    )
                    gr.Examples(
                        examples=[[example] for example in EXAMPLE_PROMPTS],
                        inputs=prompt,
                        label="A little inspiration",
                        examples_per_page=4,
                    )

                with gr.Column(scale=3):
                    raw_output = gr.Image(label="Generated output", type="pil")
                    final_output = gr.Image(label="Final image", type="pil")

            with gr.Accordion("Advanced settings", open=False):
                with gr.Row():
                    with gr.Column(scale=1):
                        postprocess = gr.Checkbox(value=True, label="Post-process output")
                    with gr.Column(scale=1):
                        enhance = gr.Checkbox(value=True, label="Prompt enhancement")
                with gr.Row(equal_height=False):
                    candidate_count = gr.Dropdown(
                        choices=["Auto", "1", "2", "3", "4"],
                        value="Auto",
                        label="Candidates",
                    )
                    tier = gr.Dropdown(
                        choices=["Auto", "Max", "High", "Medium", "Low"],
                        value="Auto",
                        label="Generation tier",
                    )
                    seed = gr.Number(value=42, precision=0, label="Seed")

            info_output = gr.Markdown(label="Generation information")
            intermediate_output = gr.Gallery(
                label="Processing intermediates",
                columns=3,
                height="auto",
            )
            candidate_output = gr.Gallery(
                label="Candidates",
                columns=4,
                height=240,
            )
            quality_output = gr.JSON(label="Quality and artifact report")
            controller_output = gr.JSON(label="Controller decisions")

            generate_button.click(
                fn=generate,
                inputs=[prompt, tier, postprocess, enhance, candidate_count, seed],
                outputs=[
                    raw_output,
                    final_output,
                    info_output,
                    intermediate_output,
                    candidate_output,
                    quality_output,
                    controller_output,
                ],
            )

        with gr.Column(scale=1, min_width=180):
            gr.HTML(side_gallery_html("right"))


def _pick_server_port(start_port=7860, max_tries=20):
    import socket

    for port in range(start_port, start_port + max_tries):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    return start_port


if __name__ == "__main__":
    launch_options = (
        theme_options
        if "css" in inspect.signature(demo.launch).parameters
        else {}
    )
    requested_port = os.environ.get("GRADIO_SERVER_PORT") or os.environ.get("PORT")
    server_port = int(requested_port) if requested_port else _pick_server_port()
    if requested_port:
        try:
            from socket import socket

            with socket() as s:
                s.bind(("127.0.0.1", int(requested_port)))
        except OSError:
            server_port = _pick_server_port(int(requested_port))
    demo.queue().launch(
        **launch_options,
        server_name=os.getenv("HOST", "127.0.0.1"),
        server_port=server_port,
        share=os.environ.get("SHARE") == "1",
    )
