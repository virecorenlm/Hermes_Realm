# Vision capability

`scripts/hailo_vision_capture.py` is an optional example for a camera and Hailo accelerator. Install the vendor runtime, a compatible HEF model, and Python OpenCV on a supported machine. Select your camera and model paths locally; no particular camera or accelerator is part of the default installation.

For normalized detection boxes, scale x coordinates by frame width and y coordinates by frame height, then clip to the image bounds. Review model output shapes and any required non-maximum suppression before using the annotations. Avoid publishing captured frames or local device inventory without operator approval.
