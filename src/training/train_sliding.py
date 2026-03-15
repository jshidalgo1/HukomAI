import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification, TrainingArguments
from torch.utils.data import Dataset
import numpy as np
from sklearn.metrics import accuracy_score, f1_score
from sklearn.utils.class_weight import compute_class_weight
from .utils import load_and_split_data, CustomTrainer

# --- CONFIG ---
MODEL_NAME = "bert-base-multilingual-cased"
MAX_LEN = 512
BATCH_SIZE = 16
EPOCHS = 2 # Reduced epochs because dataset is bigger (chunks)

def tokenize_sliding_window(texts, labels, tokenizer):
    """
    Expands the dataset by chunking long texts.
    Returns lists of inputs ready for the model.
    """
    all_input_ids = []
    all_masks = []
    all_labels = []

    print("Chunking data (Sliding Window)... this takes RAM...")
    
    # Batch encode is faster
    # stride=128 means chunks overlap by 128 tokens context
    encodings = tokenizer(
        texts, 
        truncation=True, 
        padding="max_length", 
        max_length=MAX_LEN, 
        return_overflowing_tokens=True, 
        stride=128, 
        return_tensors="pt"
    )

    # Map chunks back to original labels
    # 'overflow_to_sample_mapping' tells us which original text a chunk belongs to
    sample_map = encodings.pop("overflow_to_sample_mapping")
    
    for i, sample_idx in enumerate(sample_map):
        all_input_ids.append(encodings['input_ids'][i])
        all_masks.append(encodings['attention_mask'][i])
        all_labels.append(labels[sample_idx]) # Assign original label to this chunk

    return all_input_ids, all_masks, all_labels

class SlidingDataset(Dataset):
    def __init__(self, input_ids, masks, labels):
        self.input_ids = input_ids
        self.masks = masks
        self.labels = labels

    def __len__(self):
        return len(self.labels)

    def __getitem__(self, idx):
        return {
            'input_ids': self.input_ids[idx],
            'attention_mask': self.masks[idx],
            'labels': torch.tensor(self.labels[idx], dtype=torch.long)
        }

def compute_metrics(pred):
    labels = pred.label_ids
    preds = pred.predictions.argmax(-1)
    acc = accuracy_score(labels, preds)
    f1 = f1_score(labels, preds, average='macro')
    return {'accuracy': acc, 'f1_macro': f1}

# --- MAIN ---
if __name__ == "__main__":
    # 1. Load Data
    (train_txt, train_lbl), (val_txt, val_lbl), _ = load_and_split_data()
    
    # 2. Class Weights
    class_weights = compute_class_weight('balanced', classes=np.unique(train_lbl), y=train_lbl)

    # 3. Tokenize & CHUNK (The Magic Step)
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    
    train_ids, train_masks, train_labels_expanded = tokenize_sliding_window(train_txt, train_lbl, tokenizer)
    val_ids, val_masks, val_labels_expanded = tokenize_sliding_window(val_txt, val_lbl, tokenizer)
    
    print(f"Original Train Size: {len(train_txt)} -> Chunked Size: {len(train_labels_expanded)}")

    # 4. Create Datasets
    train_dataset = SlidingDataset(train_ids, train_masks, train_labels_expanded)
    val_dataset = SlidingDataset(val_ids, val_masks, val_labels_expanded)

    model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME, num_labels=4)

    # 5. Training Args
    training_args = TrainingArguments(
        output_dir='./results_sliding',
        num_train_epochs=EPOCHS,
        per_device_train_batch_size=BATCH_SIZE,
        per_device_eval_batch_size=BATCH_SIZE,
        warmup_steps=500,
        weight_decay=0.01,
        logging_dir='./logs_sliding',
        logging_steps=100,
        evaluation_strategy="epoch",
        save_strategy="epoch",
        fp16=True, 
        load_best_model_at_end=True,
    )

    # 6. Train
    trainer = CustomTrainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        compute_metrics=compute_metrics,
        class_weights=class_weights
    )

    trainer.train()
    trainer.save_model("./hukom_model_sliding")
    print("Strategy B (Sliding Window) Training Complete!")