import inspect
import os
import re

import gradio as gr

from src.adaptive import TIERS, generate_with_fallback
from src.ui_theme import CSS, HEAD, HERO_HTML, make_theme


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

    if result.get("ip_warning"):
        gr.Warning(result["ip_warning"])
        return None, None, "", [], [], {}, {}

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
    gr.HTML(HERO_HTML)
    with gr.Row():
        prompt = gr.Textbox(
            label="Prompt",
            placeholder="Describe the image you want to create...",
            lines=2,
        )
        tier = gr.Dropdown(
            choices=["Auto", "Max", "High", "Medium", "Low"],
            value="Auto",
            label="Generation tier",
        )
    with gr.Row():
        postprocess = gr.Checkbox(value=True, label="Post-process output")
        enhance = gr.Checkbox(value=True, label="Prompt enhancement")
        candidate_count = gr.Dropdown(
            choices=["Auto", "1", "2", "3", "4"],
            value="Auto",
            label="Candidates",
        )
        seed = gr.Number(value=42, precision=0, label="Seed")
        generate_button = gr.Button(
            "Generate",
            variant="primary",
            elem_id="flicker-generate",
        )

    gr.Examples(
        examples=[[example] for example in EXAMPLE_PROMPTS],
        inputs=prompt,
        label="Example prompts",
    )

    with gr.Row():
        raw_output = gr.Image(label="Raw image", type="pil")
        final_output = gr.Image(label="Final image", type="pil")

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


if __name__ == "__main__":
    launch_options = (
        theme_options
        if "css" in inspect.signature(demo.launch).parameters
        else {}
    )
    demo.queue().launch(
        **launch_options,
        server_name=os.getenv("HOST", "127.0.0.1"),
        server_port=int(os.environ.get("PORT", "7860")),
        share=os.environ.get("SHARE") == "1",
    )
