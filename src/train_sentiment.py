from pathlib import Path
import random, numpy as np, torch, argparse
from datasets import load_dataset, ClassLabel, Features, Value
from transformers import (AutoTokenizer, AutoModelForSequenceClassification,
                          TrainingArguments, Trainer, pipeline)
import evaluate

# --------------------------------------------------------------------------- #
# 1. globals & reproducibility
# --------------------------------------------------------------------------- #
CLASSES = ["Bearish", "Neutral", "Bullish"]          # order **must** match model
fix_seed = lambda s=42: (random.seed(s),
                         np.random.seed(s),
                         torch.manual_seed(s))

# --------------------------------------------------------------------------- #
# 2. helpers
# --------------------------------------------------------------------------- #
def tokenize(batch):
    return tok(batch["text"],
               padding="max_length",
               truncation=True,
               max_length=128)

f1_metric = evaluate.load("f1")
def compute_metrics(eval_pred):
    preds, labels = eval_pred
    preds = preds.argmax(axis=-1)
    f1   = f1_metric.compute(predictions=preds,
                             references=labels,
                             average="macro")["f1"]
    acc  = (preds == labels).mean()
    return {"accuracy": acc, "f1": f1}

# --------------------------------------------------------------------------- #
# 3. CLI
# --------------------------------------------------------------------------- #
ap = argparse.ArgumentParser()
ap.add_argument("--csv",    default="../train_data/news_dataset_mapped.csv")
ap.add_argument("--outdir", default="../models/miniLM-ft")
ap.add_argument("--epochs", type=int, default=3)
ap.add_argument("--batch",  type=int, default=4)   # fits into ~3 GB RAM
ap.add_argument("--accum",  type=int, default=8)   # → effective batch-32
args = ap.parse_args()

fix_seed()

# --------------------------------------------------------------------------- #
# 4. dataset
# --------------------------------------------------------------------------- #
label_feature = ClassLabel(names=CLASSES)
csv_features = Features(
    {
        "text":  Value("string"),
        "label": label_feature
    }
)
ds = load_dataset(
        "csv",
        data_files=args.csv,
        features=csv_features,
     )["train"]

ds = ds.train_test_split(test_size=0.1, seed=42)
print(ds)

# --------------------------------------------------------------------------- #
# 5. model & tokenizer
# --------------------------------------------------------------------------- #
CKPT = "microsoft/Multilingual-MiniLM-L12-H384"
tok  = AutoTokenizer.from_pretrained(CKPT)

model = AutoModelForSequenceClassification.from_pretrained(
            CKPT,
            num_labels=len(CLASSES),
            id2label=dict(enumerate(CLASSES)),
            label2id={c: i for i, c in enumerate(CLASSES)}
        )

# --------------------------------------------------------------------------- #
# 6. tokenise
# --------------------------------------------------------------------------- #
ds = ds.map(tokenize, batched=True, remove_columns=["text"])
ds.set_format("torch")

# --------------------------------------------------------------------------- #
# 7. training
# --------------------------------------------------------------------------- #
training_args = TrainingArguments(
    output_dir                  = args.outdir,
    overwrite_output_dir        = True,
    eval_strategy               = "epoch",
    logging_strategy            = "steps",
    save_strategy               = "steps",
    save_steps                  = 250,
    learning_rate               = 2e-5,
    per_device_train_batch_size = args.batch,
    per_device_eval_batch_size  = args.batch,
    gradient_accumulation_steps = args.accum,
    num_train_epochs            = args.epochs,
    load_best_model_at_end      = True,
    metric_for_best_model       = "f1",
    logging_steps               = 50,
    fp16                        = False,  # CPU training
)

trainer = Trainer(
    model=model,
    args=training_args,
    tokenizer=tok,
    train_dataset=ds["train"],
    eval_dataset=ds["test"],
    compute_metrics=compute_metrics,
)

trainer.train()
trainer.save_model(args.outdir)
tok.save_pretrained(args.outdir)

# --------------------------------------------------------------------------- #
# 8. test
# --------------------------------------------------------------------------- #
sent_pipe = pipeline("text-classification", model=args.outdir, tokenizer=tok)
demo = ["Bitcoin plunges 12 % following SEC investigation.",
        "Ethereum edges higher as network upgrade succeeds."]
print(sent_pipe(demo))
