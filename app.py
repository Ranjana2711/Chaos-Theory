import os
import re

import gradio as gr

from src.adaptive import generate_with_fallback


EXAMPLE_PROMPTS = [
    "a red cube to the left of a blue sphere on a white table",
    "three yellow pears beside two green apples in a wooden bowl",
    "four small orange balls arranged around one large purple cube",
    "a black cat sitting between a brown dog and a white chair",
]


def generate(prompt, tier_label, postprocess, enhance, seed):
    if not prompt or not prompt.strip():
        gr.Warning("Please enter a prompt before generating.")
        return None, None, "", [], {}, {}
    if not re.search(r"[A-Za-z0-9]", prompt):
        gr.Warning("Please enter a descriptive prompt.")
        return None, None, "", [], {}, {}

    tier = "auto" if tier_label == "Auto" else tier_label
    try:
        result = generate_with_fallback(
            prompt=prompt,
            tier=tier,
            seed=int(seed),
            postprocess=postprocess,
            enhance=enhance,
        )
    except ValueError as error:
        gr.Warning(str(error))
        return None, None, "", [], {}, {}
    except Exception as error:
        raise gr.Error(f"Image generation failed: {error}") from error

    info = (
        f"**Tier used:** {result['tier_used']}  \n"
        f"**Reason:** {result['reason']}  \n"
        f"**Fallback:** {'Yes' if result['fallback_happened'] else 'No'}  \n"
        f"**Artifact retry:** {'Yes' if result.get('artifact_retry') else 'No'}  \n"
        f"**Enhanced prompt:** {result['enhanced_prompt']}  \n"
        f"**Generation latency:** {result['latency_s']:.2f} s  \n"
        f"**Load time:** {result['load_time_s']:.2f} s  \n"
        f"**Peak memory:** {result['peak_mem_mb']:.1f} MB"
    )
    gallery = [
        (image, step_name)
        for step_name, image in result["intermediates"]
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
        quality,
        controller_decisions,
    )


with gr.Blocks(title="Chaos Theory — Text-to-Image") as demo:
    gr.Markdown(
        "# Chaos Theory — Resource-Efficient Text-to-Image\n"
        "Generate an image from a prompt with adaptive compute tiers."
    )
    with gr.Row():
        prompt = gr.Textbox(
            label="Prompt",
            placeholder="Describe the image you want to create...",
            lines=2,
        )
        tier = gr.Dropdown(
            choices=["Auto", "High", "Medium", "Low"],
            value="Auto",
            label="Generation tier",
        )
    with gr.Row():
        postprocess = gr.Checkbox(value=True, label="Post-process output")
        enhance = gr.Checkbox(value=True, label="Prompt enhancement")
        seed = gr.Number(value=42, precision=0, label="Seed")
        generate_button = gr.Button("Generate", variant="primary")

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
    quality_output = gr.JSON(label="Quality and artifact report")
    controller_output = gr.JSON(label="Controller decisions")

    generate_button.click(
        fn=generate,
        inputs=[prompt, tier, postprocess, enhance, seed],
        outputs=[
            raw_output,
            final_output,
            info_output,
            intermediate_output,
            quality_output,
            controller_output,
        ],
    )


if __name__ == "__main__":
    demo.queue().launch(
        server_name=os.getenv("HOST", "127.0.0.1"),
        server_port=int(os.environ.get("PORT", "7860")),
        share=os.environ.get("SHARE") == "1",
    )
