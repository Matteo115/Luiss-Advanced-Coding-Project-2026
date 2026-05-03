from datasets import load_dataset
import pandas as pd
import os

# 1. Load the dataset in streaming mode
# This doesn't download the whole thing to RAM; it reads it on the fly
ds = load_dataset("dmariaa70/METRAQ-Air-Quality", split="train", streaming=True)

output_file = "metraq_air_quality.csv"
chunk_size = 100000  # Number of rows to process at a time
batch = []

print("Starting export...")

for i, example in enumerate(ds):
    batch.append(example)
    
    # Once we hit the chunk size, append to the CSV
    if (i + 1) % chunk_size == 0:
        df_chunk = pd.DataFrame(batch)
        
        # Write header only for the first chunk
        mode = 'w' if i + 1 == chunk_size else 'a'
        header = True if i + 1 == chunk_size else False
        
        df_chunk.to_csv(output_file, mode=mode, index=False, header=header)
        
        print(f"Processed {i + 1} rows...")
        batch = [] # Clear memory

# Catch any remaining rows in the final batch
if batch:
    pd.DataFrame(batch).to_csv(output_file, mode='a', index=False, header=False)

print(f"Done! Dataset saved to {output_file}")