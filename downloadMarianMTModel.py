from transformers import MarianMTModel, MarianTokenizer
# model_name = "Helsinki-NLP/opus-mt-tc-big-en-ar"
model_name = "gimmeursocks/opus-mt-tc-big-en-ar-distilled"

tokenizer = MarianTokenizer.from_pretrained(model_name)
model = MarianMTModel.from_pretrained(model_name)
tokenizer.save_pretrained("models/marianmt_en_ar")
model.save_pretrained("models/marianmt_en_ar_distilled")
# this file will edit to download the optimized translation model that 	gimmeursocks work on it
# please hammed give me the model😘