#!/usr/bin/env python3
import sys, json
from PIL import Image
import numpy as np
import onnxruntime as ort

def preprocess(p):
    img = Image.open(p).convert("RGB").resize((224, 224))
    return np.array(img).astype("float32") / 255.0

def main():
    if len(sys.argv) < 3:
        print(json.dumps({"error": "Usage: cnn_runner.py <model.onnx> <image_path>"})); sys.exit(2)
    model_path, image_path = sys.argv[1], sys.argv[2]
    try:
        x = preprocess(image_path)[None, ...]          # (1,224,224,3)
        sess = ort.InferenceSession(model_path, providers=["CPUExecutionProvider"])
        inp = sess.get_inputs()[0].name
        y = sess.run(None, {inp: x})[0]                # expect (1,1) sigmoid
        prob = float(y[0][0]); label = int(prob >= 0.5)
        print(json.dumps({"prob": prob, "label": label})); sys.exit(0)
    except Exception as e:
        print(json.dumps({"error": f"{type(e).__name__}: {e}"})); sys.exit(1)

if __name__ == "__main__":
    main()
