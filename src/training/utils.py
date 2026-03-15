import pandas as pd
import torch
import os
from sklearn.model_selection import train_test_split
from sklearn.utils.class_weight import compute_class_weight
from transformers import Trainer

# --- CONFIGURATION ---
DATA_CSV = "hukom_dataset_final.csv"
CORPUS_DIR = "hukom_corpus_friendly"


def load_and_split_data():
    """
    Loads CSV, filters out -1 (Unknowns), and splits into Train/Val/Test.
    """
    print(f"Loading {DATA_CSV}...")
    df = pd.read_csv(DATA_CSV)

    # 1. Filter out Unknowns (-1)
    df = df[df['label'] != -1]

    # 2. Map filename to full path
    df['text_path'] = df['filename'].apply(lambda x: os.path.join(CORPUS_DIR, x))

    # 3. Read the actual text content from files
    texts = []
    labels = []
    print("Reading text files (this may take a minute)...")
    for idx, row in df.iterrows():
        try:
            with open(row['text_path'], "r", encoding="utf-8") as f:
                content = f.read()
                # Extract FACTS only (Model shouldn't see Ruling to avoid data leakage)
                if "========== FACTS ==========" in content:
                    parts = content.split("========== FACTS ==========")
                    if "========== RULING ==========" in parts[1]:
                        facts = parts[1].split("========== RULING ==========")[0].strip()
                        texts.append(facts)
                        labels.append(row['label'])
        except Exception:
            continue

    # 4. Split (80% Train, 10% Val, 10% Test)
    train_texts, test_texts, train_labels, test_labels = train_test_split(
        texts, labels, test_size=0.2, stratify=labels, random_state=42
    )
    val_texts, test_texts, val_labels, test_labels = train_test_split(
        test_texts, test_labels, test_size=0.5, stratify=test_labels, random_state=42
    )

    print(f"Data Loaded: {len(train_texts)} Train, {len(val_texts)} Val, {len(test_texts)} Test")

    return (train_texts, train_labels), (val_texts, val_labels), (test_texts, test_labels)


class CustomTrainer(Trainer):
    """
    Overrides the standard Trainer to add Class Weights.
    This solves the imbalance where Label 1 (Conviction) dominates.
    """
    def __init__(self, *args, class_weights=None, **kwargs):
        super().__init__(*args, **kwargs)
        if class_weights is not None:
            self.class_weights = torch.tensor(class_weights, dtype=torch.float32).to(self.args.device)
        else:
            self.class_weights = None

    def compute_loss(self, model, inputs, return_outputs=False, num_items_in_batch=None):
        labels = inputs.get("labels")
        outputs = model(**inputs)
        logits = outputs.get("logits")

        if self.class_weights is not None:
            loss_fct = torch.nn.CrossEntropyLoss(weight=self.class_weights)
            loss = loss_fct(logits.view(-1, self.model.config.num_labels), labels.view(-1))
        else:
            loss_fct = torch.nn.CrossEntropyLoss()
            loss = loss_fct(logits.view(-1, self.model.config.num_labels), labels.view(-1))

        return (loss, outputs) if return_outputs else loss
