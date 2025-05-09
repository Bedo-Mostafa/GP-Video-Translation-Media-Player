# from transformers import MarianMTModel, MarianTokenizer
# # model_name = "Helsinki-NLP/opus-mt-tc-big-en-ar"
# model_name = "gimmeursocks/opus-mt-tc-big-en-ar-distilled"

# tokenizer = MarianTokenizer.from_pretrained(model_name)
# model = MarianMTModel.from_pretrained(model_name)
# tokenizer.save_pretrained("models/marianmt_en_ar")
# model.save_pretrained("models/marianmt_en_ar_distilled")
# # this file will edit to download the optimized translation model that 	gimmeursocks work on it
# # please hammed give me the model😘

import torch
torch.cuda.init()
print(torch.cuda.get_device_capability(0))
print(torch.cuda.get_device_name(0))
print("CUDA Available:", torch.cuda.is_available())
print("CUDA Device:", torch.cuda.get_device_name(
    0) if torch.cuda.is_available() else "None")
print("CUDA Version:", torch.version.cuda)
