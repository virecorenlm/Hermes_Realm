---
name: hailo-8-vision-inference
description: Standalone Hailo-8 vision inference for multi-model pipelines, reverse-engineering compiled postprocessors into pure Python, and coordinate mapping.
---

# Hailo-8 Vision Inference

## When to load
- Building or modifying a **standalone** Hailo-8 inference script for vision models (face detection, pose estimation, object detection, segmentation) on the Pi 5 or any ARM64 node with a Hailo-8 accelerator.
- Need to run two or more Hailo models in sequence on the same video or image stream.
- Need to reproduce compiled `.so` postprocessor logic in pure Python/NumPy to avoid `hailo_apps` framework dependencies.
- Working with the Hailo Raspberry Pi Developer Zone package at `~/hailo-apps`.

## Key Patterns

### 1. Sequential Multi-Model Inference with Shared VDevice
**CRITICAL:** Always create **one** `VDevice` and pass it to all `HailoInfer` instances. Creating two separate `VDevice` objects for the same physical Hailo-8 causes a **kernel segfault** in `hailo_vdma_buffer_map` when the second model tries to configure DMA buffers:
```python
params = VDevice.create_params()
params.scheduling_algorithm = HailoSchedulingAlgorithm.ROUND_ROBIN
params.group_id = "SHARED"
vdevice = VDevice(params)                          # ONE device handle

scrfd_infer = HailoInfer(scrfd_hef, vdevice=vdevice)
pose_infer  = HailoInfer(pose_hef,  vdevice=vdevice)
```
Run model inferences sequentially (pass 1, then pass 2). Do not launch overlapping `run_async` calls across different configured models on the same VDevice.

### 2. VDevice has no `.close()`
The `VDevice` class in recent `hailo_platform` versions has **no `.close()` method**. Tear down by exiting the configured model context (`self.config_ctx.__exit__()`), not by calling `vdevice.close()`. Calling the nonexistent method raises `AttributeError`.

### 3. Reverse-Engineering Compiled Postprocessors
The Hailo Developer Zone ships compiled `.so` postprocessors in `hailo_apps/postprocess/build.release/cpp/`. To write a standalone NumPy equivalent:
1. Run `nm -D lib<name>.so` to find exported functions.
2. Read the corresponding C++ source in `hailo_apps/postprocess/cpp/<name>.cpp` and `.hpp`.
3. Port anchor generation, bbox decode, score thresholds, and NMS logic into NumPy.
4. Verify tensor shapes by introspecting the HEF:
```python
from hailo_platform import HEF
hef = HEF(hef_path)
for layer in hef.get_output_vstream_infos():
    print(layer.name, layer.shape)
```

### 3. Letterbox Preprocessing with Inverse Mapping
Hailo models expect square inputs (e.g., 640×640). Preprocess with `cv2.resize` + padding, but track `scale` and `pad` (top, left) so you can map results back to original coordinates. See the `letterbox` implementation in `templates/hailo_standalone_inference.py`.

### 4. Crop Expansion for Multi-Stage Detection → Pose
When a face detector gives a tight face box but the pose model needs shoulders and hips, expand the crop around the face center:
- **Horizontal expansion:** ~2× face box width
- **Vertical expansion:** ~3× face box height
This places the face in the upper third of the crop and usually includes torso keypoints.

### 5. On-TPU NMS Models Return Normalized Coordinates (0–1)
YOLOv10x, YOLOv7e6, and similar HEFs that ship with built-in NMS post-processing (`HAILO_NMS_WITH_BYTE_MASK`) emit **normalized** bbox coordinates `[x_min, y_min, x_max, y_max]` in the range **0 to 1**, NOT pixel coordinates relative to the model input size.

Code that assumes pixel coords will draw boxes 1000× too large. Always scale by original frame dimensions:
```python
x1 = int(x_norm * frame_w)
y1 = int(y_norm * frame_h)
```

Output shape for these models is `(B, num_classes, num_attrs, max_dets)` where `num_attrs ≥ 4` (bbox coords + confidence) and the remaining slots are class-specific detections already pruned by NMS.

### 6. Two Valid Standalone Inference Patterns
| Pattern | Best For | Complexity |
|---------|----------|------------|
| `VDevice.create_infer_model()` + async | Streaming, multi-model shared VDevice | Higher (see template) |
| `hp.InferVStreams()` + sync one-shot | Single image / frame capture scripts | Lower |

For a quick webcam→detection script, `InferVStreams` is enough:
```python
with hp.VDevice() as vdevice:
    configure_params = hp.ConfigureParams.create_from_hef(hef=hef, interface=hp.HailoStreamInterface.PCIe)
    network_group = vdevice.configure(hef, configure_params)[0]
    with hp.InferVStreams(network_group, hp.InputVStreamParams.make(network_group),
                         hp.OutputVStreamParams.make(network_group)) as pipeline:
        with network_group.activate(network_group.create_params()):
            output = pipeline.infer(input_data)
```

### 6. Compile to Hailo
   - Export ONNX.
   - Compile through Hailo Dataflow Compiler / Model Zoo path available on the Pi or dev box.
   - Store final `.hef` under a stable path such as `~/.config/hermes-realm/models/hailo/lure_recognition.hef`.

### 7. Training a Custom Lure-Recognition Model (Dataset → HEF)

This subsection covers the Vire / Qdrant-planned fishing-lure recognition pipeline:
- Collect images from real inventory, Shopify exports, and vendor reference sites
- Label by type (Crankbait, Jerkbait, Topwater, …), brand, color pattern, and condition
- Build multi-label PyTorch baseline first, then export ONNX and compile to `.hef`

**Label vocabulary:**

Types: Glide Bait, Crankbait, Jerkbait, Swimbait, Topwater, Spinnerbait, Buzzbait, Jig, Soft Plastic, Spoon

Brands: River Run, Chaos Tackle, Phantom Lures, River2sea, Bagley Baits, Bomber Lures, Sebile, Megabass, Deps, Strike King, Rapala, Unknown

Conditions: New, Like New, Excellent, Good, Fair, Used

Colors: Fire Tiger, Black, White, Chartreuse, Perch, Shad, Bluegill, Crawfish, Gold, Silver, Bone, Clown

**Dataset layout:**
```
~/.config/hermes-realm/datasets/lures/
  raw/{phone_uploads,shopify_exports,vendor_reference}/
  annotations/lure_dataset_annotations.json
  processed/{train,val,test}/
  reports/
  models/{checkpoints,lure_recognition.onnx,lure_recognition.hef}
```

**Key training rules:**
- Split by product/source, not random image, to avoid near-duplicate leakage
- Start with CPU/GPU trainable PyTorch baseline before Hailo compilation
- Do NOT mix pristine vendor images with used-shop condition labels
- Do NOT treat low-confidence brand output as truth — flag `needs_review`

**Inference output contract:**
```json
{
  "model": "lure_recognition.hef",
  "image_path": "...",
  "predictions": {
    "lure_type": {"label": "Crankbait", "confidence": 0.91},
    "brand": {"label": "Unknown", "confidence": 0.34},
    "condition": {"label": "Good", "confidence": 0.72},
    "colors": [{"label": "Fire Tiger", "confidence": 0.87}]
  },
  "quality_flags": ["brand_uncertain"],
  "needs_review": true
}
```

## Hailo Whisper ASR Server on Pi 5

Use this when the operator asks for the older Hailo Whisper backend instead of Faster Whisper.

Canonical project:
`${HERMES_REALM_HOME:-$HOME/.config/hermes-realm}/projects/wyoming-hailo-whisper-main`

Base English model files for Hailo-8:
- Encoder: `wyoming_hailo_whisper/app/hefs/h8/base/base-whisper-encoder-5s.hef`
- Decoder: `wyoming_hailo_whisper/app/hefs/h8/base/base-whisper-decoder-fixed-sequence-matmul-split.hef`

Start the Wyoming Hailo Whisper server for base English on the legacy/local voice port expected by Vire scripts:

```bash
cd ${HERMES_REALM_HOME:-$HOME/.config/hermes-realm}/projects/wyoming-hailo-whisper-main
python3 -u -m wyoming_hailo_whisper \
  --uri tcp://0.0.0.0:10300 \
  --device hailo8 \
  --variant base \
  --language en \
  2>&1 | tee ${HERMES_REALM_HOME:-$HOME/.config/hermes-realm}/logs/hailo_whisper_base_server.log
```

Use Hermes `terminal(background=true, watch_patterns=["Ready", "Traceback"])` for this server. Do not wrap it with `nohup` or shell `&` inside a foreground terminal call.

Verify it is serving:

```bash
python3 - <<'PY'
import asyncio
from wyoming.client import AsyncClient
from wyoming.info import Describe, Info
async def main():
    async with AsyncClient.from_uri('tcp://127.0.0.1:10300') as client:
        await client.write_event(Describe().event())
        event = await asyncio.wait_for(client.read_event(), timeout=5)
        info = Info.from_event(event)
        print(event.type, [p.name for p in info.asr])
asyncio.run(main())
PY
```

Expected result:
`info ['hailo-whisper']`

Notes:
- `--variant base --language en` is the practical equivalent of the operator's “base.en” request for this Wyoming Hailo server.
- Port `10300` is what `${HERMES_REALM_HOME:-$HOME/.config/hermes-realm}/scripts/test_wyoming.py` and `wyoming_http_bridge.py` expect.
- Home Assistant examples commonly use `10600`; avoid that unless explicitly setting up HA integration.
- The server may briefly query Hugging Face for the Whisper tokenizer and log a harmless `additional_chat_templates` 404 before reporting `Ready`.

## Pitfalls
- **Tensor output order is NOT alphabetical.** Always introspect with `HEF.get_output_vstream_infos()` before hardcoding tensor indices or names.
- **Channel dimension placement varies.** The Python Hailo API may return NHWC or NCHW depending on network script configuration. Use `FLOAT32` output format for automatic dequantization but verify the resulting rank and shape.
- **Async callback lifetime.** When using `infer_model.run_async(frame, callback)`, the callback must capture results into a mutable container before the function returns, and you must ensure the async operation completes before reusing the input buffer.
- **Do NOT import `hailo_apps.core` or pipeline utilities if the user asked for a standalone script.** Use only `hailo_platform`, `numpy`, `cv2`, and Python stdlib.
- **CV2 VideoCapture on Pi 5 defaults to GStreamer backend.** The harmless `GStreamer warning: pipeline have not been created` on first open is normal; frames still capture fine. No fix needed.
- **Lighting sensitivity on Hailo-8 YOLO models.** Bright close-source lights cause bloom/glare which reduces detection confidence and produces looser bounding boxes. Turning off overhead lighting near the camera *increased* person detection confidence from 92% → 95% in live testing (2026-06-14).

## References
- `references/scrfd-yolov8-pose-postprocess.md` — SCRFD anchor formulas, bbox decode logic, and YOLOv8-pose tensor slicing for the face→pose tracker.
- `references/scrfd-shape-pitfalls.md` — Tensor shape dimension traps, DMA multi-model segfault, and VDevice cleanup gotchas discovered while building a face+pose pipeline (2026-06-09).
- `references/nms-normalized-coords.md` — On-TPU NMS output format, normalized coordinate mapping, and false-positive tuning for YOLOv10x / YOLOv7e6.
- `references/hailo-webcam-vision-live-20250614.md` — Live webcam capture session: lighting sensitivity, GStreamer backend behavior, YOLOv10x bbox coordinates, timing benchmarks.
- `references/redis-jemalloc-pi5-arm64-fix.md` — Building Redis from source with `MALLOC=libc` on Pi 5 ARM64 to fix jemalloc/16KB page-size SIGSEGV.
- `templates/hailo_standalone_inference.py` — Minimal standalone HailoInfer wrapper with shared VDevice pattern and preprocessing scaffold.
- `templates/hailo_one_shot_capture.py` — Webcam capture → Hailo detection → annotated frame + text description, using `InferVStreams` sync pattern.
- `templates/hailo_one_shot_capture.py` — Webcam capture → Hailo detection → annotated frame + text description, using `InferVStreams` sync pattern.
