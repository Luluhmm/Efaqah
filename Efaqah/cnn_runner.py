#!/usr/bin/env python3
# cnn_runner.py
import sys, json
from pathlib import Path
from PIL import Image
import numpy as np
# pyright: reportMissingImports=false

import tensorflow as tf
from tensorflow.keras.models import load_model

def preprocess(img_path: str):
    img = Image.open(img_path).convert("RGB").resize((224, 224))
    arr = np.array(img).astype("float32") / 255.0
    return arr

def main():
    if len(sys.argv) < 3:
        print(json.dumps({"error": "Usage: cnn_runner.py <model_path> <image_path>"}))
        sys.exit(2)

    model_path = sys.argv[1]
    image_path = sys.argv[2]

    try:
        model = load_model(model_path, compile=False)
        x = preprocess(image_path)[None, ...]  # (1, 224, 224, 3) my dimensions
        prob = float(model.predict(x, verbose=0)[0][0])  
        label = int(prob >= 0.5)  # threshold 0.5 by default
        print(json.dumps({"prob": prob, "label": label}))
        sys.exit(0)
    except Exception as e:
        print(json.dumps({"error": f"{type(e).__name__}: {e}"}))
        sys.exit(1)

if __name__ == "__main__":
    main()