

from datasets import load_dataset
import pandas as pd

# Login using e.g. `huggingface-cli login` to access this dataset
ds = load_dataset("dmariaa70/METRAQ-Air-Quality")

# Save the whole thing to a local folder (very fast, uses Arrow format)
ds.save_to_disk("./metraq_local_data")