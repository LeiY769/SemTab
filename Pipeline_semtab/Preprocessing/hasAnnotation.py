import os
import glob
import pandas as pd

def get_csv_files(input_folder):
    annotation_files = glob.glob(os.path.join(input_folder, '*.csv'))
    file_list = []
    for file_path in annotation_files:
        file_name = os.path.basename(file_path)
        file_list.append(file_name)
    return file_list
    
def hasAnnotation(config):
    input_folder = config["INPUT_FOLDER"]
    output_folder = config["OUTPUT_FOLDER"]
    target_folder = config["TARGET_FOLDER"]

    input_files = get_csv_files(input_folder)

    if output_folder is None:
        output_folder = input_folder + "_annotated"
        os.makedirs(output_folder)
    else:
        if output_folder == input_folder:
            print("Take care to know ,You overwrite original files.")
        elif not os.path.exists(output_folder):
            os.makedirs(output_folder)

    cea_file = pd.read_csv(os.path.join(target_folder, "cea_targets.csv"),header=None)
    cta_file = pd.read_csv(os.path.join(target_folder, "cta_targets.csv"),header=None)
    cpa_file = pd.read_csv(os.path.join(target_folder, "cpa_targets.csv"),header=None)

    for file in input_files:
        file_path = file 
        filename_no_ext = os.path.splitext(file)[0]
        data = pd.read_csv(os.path.join(input_folder, file_path))
        
        cea_annotations = cea_file[cea_file[0] == filename_no_ext]
        cta_annotations = cta_file[cta_file[0] == filename_no_ext]
        cpa_annotations = cpa_file[cpa_file[0] == filename_no_ext]

        get_all_cta = cta_annotations[1].tolist()
        get_all_tuples_cpa = cpa_annotations[[1,2]].values.tolist()

        new_column = "Metadata:" + "CTA:" + str(get_all_cta) + ",CPA:" + str(get_all_tuples_cpa)
        data[new_column] = [[] for _ in range(len(data))]
        for i in range(len(cea_annotations)):
            row = int(cea_annotations.iloc[i][1]) - 1
            column = int(cea_annotations.iloc[i][2])
            data.at[row,new_column].append(column) 
        output_file = os.path.join(output_folder, file_path)
        data.to_csv(output_file, index=False)
    



        