# Flicker Failure Cases

Each image link below is a placeholder for a failure illustration; no image files are included.

## Object count and color binding

| Field | Observation |
|---|---|
| Prompt | “three blue cups to the left of two yellow bananas” |
| Tier | High |
| Expected | Three blue cups to the left of two yellow bananas |
| Actual | About ten bananas and no blue cups |
| Root cause | Weak object counting and color-to-object binding |
| Mitigation | The adaptive system can try higher tiers and compare candidates, but the supplied observation did not establish a successful correction |
| Outcome | Failure remains unresolved in the reported example |

![Object count and color binding failure placeholder](failures/object-count-color-binding.png)

## Text and franchise-name prompt

| Field | Observation |
|---|---|
| Prompt | A prompt containing a franchise name |
| Tier | Not supplied |
| Expected | Readable text and a faithful depiction of the requested subject |
| Actual | Garbled text: “Pekémciov”; the generation also imitates trademarked characters |
| Root cause | The text encoder represents tokens rather than spelling out letters; the model can reproduce trademarked visual subjects |
| Mitigation | No successful mitigation was reported; use caution with generated text and branded or copyrighted subjects |
| Outcome | Text rendering and imitation remain limitations |

![Text and franchise-name failure placeholder](failures/text-and-franchise-prompt.png)

## Headphones omitted and attribute leakage

| Field | Observation |
|---|---|
| Prompt | “a cat wearing headphones sitting on a sofa” |
| Tier | High; Max was also tried |
| Expected | A cat wearing visible headphones while sitting on a sofa |
| Actual | High omitted headphones. Max also failed, showing only a partial headband; “red” moved to the sofa |
| Root cause | The model did not reliably render the accessory or bind the attribute to the intended object |
| Mitigation | Tried concrete wording, reranking, and Max |
| Outcome | The reported attempts did not fully resolve the failure |

![Headphones and attribute leakage failure placeholder](failures/headphones-attribute-leakage.png)

## Distorted small faces

| Field | Observation |
|---|---|
| Prompt | “a girl sitting in the garden with a cat” |
| Tier | Max |
| Expected | A coherent scene with recognizable faces |
| Actual | Small faces were distorted at 512×512 |
| Root cause | Small facial features are difficult to render at the evaluated image size |
| Mitigation | Use close-up framing; face restoration is future work |
| Outcome | Close-up framing is the recommended workaround; restoration has not yet been implemented |

![Distorted small faces failure placeholder](failures/distorted-small-faces.png)

## Ghost omitted

| Field | Observation |
|---|---|
| Prompt | “create a ghost in an abandoned building” |
| Tier | Not supplied |
| Expected | A visible ghost in an abandoned building |
| Actual | No ghost appeared |
| Root cause | Photo-style enhancement terms worked against the fantasy concept |
| Mitigation | The prompt enhancer was updated with mood-aware terms, leading-instruction removal, and concept expansion |
| Outcome | The reported code change targets this failure; no post-fix measurement was supplied |

![Ghost omitted failure placeholder](failures/ghost-omitted.png)

## LCM steps and guidance regression

| Field | Observation |
|---|---|
| Prompt | Evaluation prompts; no single prompt supplied |
| Tier | Fast / LCM |
| Expected | Additional sampling steps or higher guidance would improve quality enough to justify added compute |
| Actual | Eight steps scored worse than four. Guidance 1.8 also scored worse and took 35% longer than guidance 1.0 |
| Root cause | The measured fast configuration performs best at four steps and guidance 1.0; guidance above 1 requires a second UNet pass |
| Mitigation | Keep High at four steps and retain guidance 1.0 |
| Outcome | The selected fast settings reflect the measured results |

![LCM steps and guidance regression placeholder](failures/lcm-steps-guidance.png)

## Summary

| Failure | Main issue | Reported mitigation or status |
|---|---|---|
| Object count and color binding | Incorrect counts and missing color-bound objects | No successful correction reported |
| Text and franchise-name prompt | Garbled text and trademark imitation | Known limitation |
| Headphones and attribute leakage | Accessory omission and incorrect attribute binding | Concrete wording, reranking, and Max did not fully resolve it |
| Distorted small faces | Low detail in small faces | Close-up framing; face restoration is future work |
| Ghost omitted | Fantasy concept suppressed by photo-style terms | Enhancer updated; no post-fix measurement supplied |
| LCM steps and guidance regression | More compute reduced quality or increased latency | Retain four steps and guidance 1.0 |
