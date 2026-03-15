import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification, TrainingArguments
from torch.utils.data import Dataset
import numpy as np
from sklearn.metrics import accuracy_score, f1_score
from sklearn.utils.class_weight import compute_class_weight
from .utils import load_and_split_data, CustomTrainer

# --- CONFIG ---
MODEL_NAME = "bert-base-multilingual-cased" # Good for mixed English/Tagalog
MAX_LEN = 512
BATCH_SIZE = 16 # Safe for T4
EPOCHS = 3

class HeadTailDataset(Dataset):
    def __init__(self, texts, labels, tokenizer, max_len=512):
        self.texts = texts
        self.labels = labels
        self.tokenizer = tokenizer
        self.max_len = max_len

    def __len__(self):
        return len(self.texts)

    def __getitem__(self, idx):
        text = self.texts[idx]
        label = self.labels[idx]

        # 1. Tokenize without truncation first
        tokens = self.tokenizer(text, add_special_tokens=True, truncation=False, return_tensors='pt')
        input_ids = tokens['input_ids'][0]
        
        # 2. Implement Head + Tail Logic
        if len(input_ids) > self.max_len:
            # Keep [CLS] (start) + 128 tokens
            head = input_ids[:129] 
            # Keep last 382 tokens + [SEP] (end)
            tail = input_ids[-(self.max_len - 129):] 
            # Concatenate
            input_ids = torch.cat([head, tail])
        else:
            # Padding if too short
            padding = torch.zeros(self.max_len - len(input_ids), dtype=torch.long)
            input_ids = torch.cat([input_ids, padding])

        # Create attention mask (1 for real tokens, 0 for padding)
        attention_mask = (input_ids != 0).long()

        return {
            'input_ids': input_ids,
            'attention_mask': attention_mask,
            'labels': torch.tensor(label, dtype=torch.long)
        }

def compute_metrics(pred):
    labels = pred.label_ids
    preds = pred.predictions.argmax(-1)
    acc = accuracy_score(labels, preds)
    f1 = f1_score(labels, preds, average='macro') # Macro because of class imbalance
    return {'accuracy': acc, 'f1_macro': f1}

# --- MAIN ---
if __name__ == "__main__":
    # 1. Load Data
    (train_txt, train_lbl), (val_txt, val_lbl), _ = load_and_split_data()
    
    # 2. Calculate Class Weights (To fix imbalance)
    class_weights = compute_class_weight('balanced', classes=np.unique(train_lbl), y=train_lbl)
    print(f"Class Weights: {class_weights}")

    # 3. Tokenizer & Model
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME, num_labels=4)

    # 4. Datasets
    train_dataset = HeadTailDataset(train_txt, train_lbl, tokenizer)
    val_dataset = HeadTailDataset(val_txt, val_lbl, tokenizer)

    # 5. Training Arguments (Optimized for T4)
    training_args = TrainingArguments(
        output_dir='./results_headtail',
        num_train_epochs=EPOCHS,
        per_device_train_batch_size=BATCH_SIZE,
        per_device_eval_batch_size=BATCH_SIZE,
        warmup_steps=500,
        weight_decay=0.01,
        logging_dir='./logs',
        logging_steps=100,
        evaluation_strategy="epoch",
        save_strategy="epoch",
        fp16=True, # CRITICAL for T4 GPU (Saves memory)
        load_best_model_at_end=True,
    )

    # 6. Train
    trainer = CustomTrainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        compute_metrics=compute_metrics,
        class_weights=class_weights # Pass our weights here
    )

    trainer.train()
    trainer.save_model("./hukom_model_headtail")
    print("Strategy A (Head+Tail) Training Complete!")