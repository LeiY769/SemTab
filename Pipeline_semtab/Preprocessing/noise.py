
import re
import pandas as pd
import os
import glob

def remove_html_tags(text):
    if pd.isna(text) or not isinstance(text, str):
        return text
    
    new_text = re.sub(r'<[^>]+>', '', text)
    return new_text
def remove_extra_spaces(text):

    if pd.isna(text) or not isinstance(text, str):
        return text
    
    text = re.sub(r'\s+', ' ', text.strip())
    return text

def clean_text(text):
    if not isinstance(text, str):
        return text
    
    if text.startswith('"""') and text.endswith('"""'):
        text = text[3:-3]
    
    if text.startswith('**') and text.endswith('**'):
        text = text[2:-2]
    
    return text

def text_processing(text) :
    if pd.isna(text) or not isinstance(text, str):
        return text
    
    text = remove_html_tags(text)
    text = remove_extra_spaces(text)
    text = clean_text(text)
    
    return text
def process_dataframe(df, columns) :
    df = df.copy()

    if columns == 'all':
        cols_to_process = df.select_dtypes(include=['object', 'string']).columns.tolist()
    else:
        cols_to_process = [columns] if isinstance(columns, str) else columns
    
    for col in cols_to_process:
        if col in df.columns:
            df[col] = df[col].apply(lambda x: text_processing(x))
    return df


def process_csv(input_file, output_file = None, columns = 'all') :
    df = pd.read_csv(input_file)
    df_cleaned = process_dataframe(df, columns)
    
    if output_file:
        df_cleaned.to_csv(output_file, index=False)
    
    return df_cleaned

def cleanup_folder(config):
    input_folder = config["INPUT_FOLDER"]
    output_folder = config["OUTPUT_FOLDER"]

    if output_folder is None:
        output_folder = input_folder + "_cleaned"
        os.makedirs(output_folder)
    else:
        if output_folder == input_folder:
            print("Take care to know ,You overwrite original files.")
        elif not os.path.exists(output_folder):
            os.makedirs(output_folder)

    csv_files = glob.glob(os.path.join(input_folder, '*.csv'))
    
    for file_path in csv_files:
        file_name = os.path.basename(file_path)
        output_file = os.path.join(output_folder, file_name)
        process_csv(file_path, output_file, columns='all')
