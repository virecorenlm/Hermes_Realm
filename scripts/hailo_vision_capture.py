#!/usr/bin/env python3
"""
hailo_vision_capture.py — Pi 5 Hailo-8 Webcam Object Detection
Captures a frame from /dev/video0, runs YOLOv10x (or fallback YOLOv7e6) on the Hailo-8,
annotates detections, saves raw + annotated frames, and prints a natural description.

Usage:  python3 hailo_vision_capture.py
Requires: hailo_platform, opencv-python, numpy
HEF files: ~/Desktop/Downloads/*.hef
"""
import sys
import time
from pathlib import Path

try:
    import hailo_platform as hp
except ImportError as e:
    print(f"ERROR: hailo_platform not available: {e}", file=sys.stderr)
    sys.exit(1)

try:
    import cv2
    import numpy as np
except ImportError as e:
    print(f"ERROR: opencv / numpy not available: {e}", file=sys.stderr)
    sys.exit(1)

# COCO 80 class labels
COCO_LABELS = [
    "person", "bicycle", "car", "motorcycle", "airplane", "bus", "train", "truck", "boat",
    "traffic light", "fire hydrant", "stop sign", "parking meter", "bench", "bird", "cat",
    "dog", "horse", "sheep", "cow", "elephant", "bear", "zebra", "giraffe", "backpack",
    "umbrella", "handbag", "tie", "suitcase", "frisbee", "skis", "snowboard", "sports ball",
    "kite", "baseball bat", "baseball glove", "skateboard", "surfboard", "tennis racket",
    "bottle", "wine glass", "cup", "fork", "knife", "spoon", "bowl", "banana", "apple",
    "sandwich", "orange", "broccoli", "carrot", "hot dog", "pizza", "donut", "cake",
    "chair", "couch", "potted plant", "bed", "dining table", "toilet", "tv", "laptop",
    "mouse", "remote", "keyboard", "cell phone", "microwave", "oven", "toaster", "sink",
    "refrigerator", "book", "clock", "vase", "scissors", "teddy bear", "hair drier", "toothbrush"
]


def capture_webcam_frame(device="/dev/video0", warmup_frames=5):
    """Capture a frame from the webcam."""
    cap = cv2.VideoCapture(device)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open webcam at {device}")
    # Discard warmup frames (auto-exposure / white balance settling)
    for _ in range(warmup_frames):
        cap.read()
    ret, frame = cap.read()
    cap.release()
    if not ret or frame is None:
        raise RuntimeError("Failed to capture frame")
    return frame


def run_yolo_detection(hef_path, frame, confidence_threshold=0.30):
    """Run YOLO detection on a BGR (OpenCV) frame using Hailo-8."""
    hef = hp.HEF(str(hef_path))
    input_vstream_infos = hef.get_input_vstream_infos()
    output_vstream_infos = hef.get_output_vstream_infos()

    input_h, input_w, _ = input_vstream_infos[0].shape

    # Resize + BGR→RGB + add batch dim
    resized = cv2.resize(frame, (input_w, input_h))
    rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
    input_data = np.expand_dims(rgb, axis=0).astype(np.uint8)

    detections = []

    with hp.VDevice() as vdevice:
        configure_params = hp.ConfigureParams.create_from_hef(
            hef=hef, interface=hp.HailoStreamInterface.PCIe
        )
        network_group = vdevice.configure(hef, configure_params)[0]

        network_group_params = network_group.create_params()
        input_vstreams_params = hp.InputVStreamParams.make(network_group)
        output_vstreams_params = hp.OutputVStreamParams.make(network_group)

        with hp.InferVStreams(
            network_group, input_vstreams_params, output_vstreams_params
        ) as infer_pipeline:
            with network_group.activate(network_group_params):
                output = infer_pipeline.infer(input_data)

        # Parse already-NMS post-processed output.
        # Output is (B, num_classes, num_attrs, max_dets).
        # Each detection = [x_min(normalized), y_min, x_max, y_max, confidence].
        output_name = output_vstream_infos[0].name
        class_detections = output[output_name][0]  # drop batch dim

        for class_id, class_dets in enumerate(class_detections):
            if hasattr(class_dets, '__len__'):
                for det in class_dets:
                    if hasattr(det, '__len__') and len(det) >= 4:
                        x_min, y_min, x_max, y_max = det[0], det[1], det[2], det[3]
                        conf = float(det[4]) if len(det) > 4 else 1.0
                        if conf >= confidence_threshold:
                            label = COCO_LABELS[class_id] if class_id < len(COCO_LABELS) else f"class_{class_id}"
                            detections.append({
                                "label": label,
                                "confidence": float(conf),
                                "bbox": [float(x_min), float(y_min), float(x_max), float(y_max)],
                                "class_id": int(class_id)
                            })

    return detections


def describe_scene(detections, top_n=10):
    """Turn detection list into a natural description."""
    if not detections:
        return "I don't detect any objects in this scene with confidence."

    # Group by label, keep highest confidence per label
    by_label = {}
    for d in detections:
        lab = d["label"]
        if lab not in by_label or by_label[lab]["confidence"] < d["confidence"]:
            by_label[lab] = d

    # Sort by confidence
    sorted_items = sorted(by_label.items(), key=lambda kv: kv[1]["confidence"], reverse=True)

    objects = []
    for label, det in sorted_items[:top_n]:
        conf = det["confidence"]
        objects.append(f"{label} ({conf:.0%})")

    return "In this scene, I see: " + ", ".join(objects)


def main():
    # HEF selection: prefer yolov10x (640×640), fall back to yolov7e6 (1280×1280)
    hef_dir = Path.home() / "Desktop" / "Downloads"
    hef_path = hef_dir / "yolov10x.hef"
    if not hef_path.exists():
        hef_path = hef_dir / "yolov7e6.hef"
    if not hef_path.exists():
        print("ERROR: No HEF files found at ~/Desktop/Downloads")
        sys.exit(1)

    print(f"Hailo Vision Capture — using {hef_path.name}")
    print("Opening webcam /dev/video0 ...")

    t0 = time.time()
    frame = capture_webcam_frame()
    print(f"Frame captured ({frame.shape[1]}x{frame.shape[0]}) in {time.time()-t0:.2f}s")

    # Save raw capture for inspection
    capture_path = Path("/tmp/hailo_capture_raw.jpg")
    cv2.imwrite(str(capture_path), frame)
    print(f"Raw capture saved to {capture_path}")

    print("Running Hailo inference ...")
    t1 = time.time()
    detections = run_yolo_detection(hef_path, frame, confidence_threshold=0.30)
    print(f"Inference complete in {time.time()-t1:.2f}s")
    print(f"Detections: {len(detections)}")

    # Print top detections
    if detections:
        for d in sorted(detections, key=lambda x: x["confidence"], reverse=True)[:15]:
            print(f"  - {d['label']}: {d['confidence']:.2f} @ bbox {d['bbox']}")

    # Describe scene
    description = describe_scene(detections)
    print(f"\n{description}")

    # Draw boxes (normalized coords → original frame coords)
    annotated = frame.copy()
    for d in detections:
        x1, y1, x2, y2 = d["bbox"]
        # These are normalized (0–1) from TPU NMS post-processing
        x1 = int(x1 * frame.shape[1])
        x2 = int(x2 * frame.shape[1])
        y1 = int(y1 * frame.shape[0])
        y2 = int(y2 * frame.shape[0])
        cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(annotated, f"{d['label']} {d['confidence']:.2f}",
                    (x1, max(y1 - 10, 20)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

    annotated_path = Path("/tmp/hailo_capture_annotated.jpg")
    cv2.imwrite(str(annotated_path), annotated)
    print(f"Annotated capture saved to {annotated_path}")

    return description, capture_path, annotated_path


if __name__ == "__main__":
    main()
