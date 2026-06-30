"""
Backend Python Triton pour Phi-3.5-Financial
Triton Inference Server — Python Backend
"""
import json
import numpy as np
import triton_python_backend_utils as pb_utils


class TritonPythonModel:
    """
    Modèle Triton qui charge Phi-3.5-Financial via Ollama local.
    Alternative : utiliser vLLM directement.
    """

    def initialize(self, args):
        import httpx
        self.model_config = json.loads(args["model_config"])
        self.ollama_url = "http://localhost:11434"
        self.model_name = "phi3.5-financial"
        self.client = httpx.Client(timeout=120.0)
        pb_utils.Logger.log_info("Phi-3.5-Financial Triton Backend initialisé")

    def execute(self, requests):
        responses = []
        for request in requests:
            input_tensor = pb_utils.get_input_tensor_by_name(request, "INPUT_TEXT")
            input_bytes = input_tensor.as_numpy()

            results = []
            for text_bytes in input_bytes:
                text = text_bytes[0].decode("utf-8") if isinstance(text_bytes, np.ndarray) else text_bytes.decode("utf-8")

                try:
                    payload = {
                        "model": self.model_name,
                        "messages": [{"role": "user", "content": text}],
                        "stream": False,
                        "options": {"temperature": 0.7, "num_predict": 1024},
                    }
                    resp = self.client.post(f"{self.ollama_url}/api/chat", json=payload)
                    resp.raise_for_status()
                    data = resp.json()
                    output = data.get("message", {}).get("content", "")
                except Exception as e:
                    output = f"[ERREUR]: {e}"

                results.append([output.encode("utf-8")])

            output_array = np.array(results, dtype=object)
            output_tensor = pb_utils.Tensor("OUTPUT_TEXT", output_array)
            responses.append(pb_utils.InferenceResponse(output_tensors=[output_tensor]))

        return responses

    def finalize(self):
        self.client.close()
        pb_utils.Logger.log_info("Phi-3.5-Financial Triton Backend arrêté")
