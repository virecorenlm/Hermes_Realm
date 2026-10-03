---
name: vire-graphic-design
description: "Use when producing graphics with GIMP, Inkscape, or ImageMagick on an available computer."
version: 1.0.0
author: Vire Shorette
license: MIT
metadata:
  hermes:
    tags: [gimp, inkscape, imagemagick, graphics]
    related_skills: [vire, vire-video-production, vire-content-strategy]
---

# Graphic Design

Use whichever of GIMP, Inkscape, and ImageMagick is installed on the local computer.

## Batch Resize Images (GIMP scriptfu)
```bash
gimp -i -b '(let* ((image (car (gimp-file-load RUN-NONINTERACTIVE "input.jpg" "input.jpg")))
                    (drawable (car (gimp-image-get-active-drawable image))))
               (gimp-image-scale-full image 1080 1080 INTERPOLATION-LINEAR)
               (file-jpeg-save RUN-NONINTERACTIVE image drawable "output.jpg" "output.jpg" 0.9 0 0 0 "" 0 1 0 2 0)
               (gimp-quit 0))'
```

## Export SVG to PNG (Inkscape)
```bash
inkscape --export-type=png --export-width=1080 --export-height=1080 \
  input.svg -o output.png
```

## Create Social Media Graphic from Template
```bash
# scripts/make-graphic.sh <template.svg> <text> <output.png>
sed "s/{{TITLE}}/$2/g" "$1" > /tmp/graphic-filled.svg
inkscape --export-type=png --export-width=1080 /tmp/graphic-filled.svg -o "$3"
```

Templates live in `assets/templates/` — see assets folder.
