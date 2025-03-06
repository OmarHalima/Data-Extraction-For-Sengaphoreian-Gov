import pandas as pd
import re

def parse_agency_data(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()

    data = []
    agency_id, agency_name, address, phone_number = None, None, "", None

    for line in lines:
        line = line.strip()
        
        if line.startswith("Page"):  # New agency entry
            if agency_id and agency_name and address and phone_number:
                data.append([agency_id, agency_name, address.strip(), phone_number])
            agency_id, agency_name, address, phone_number = None, None, "", None
            
            agency_id_match = re.search(r'Agency ID: (.+)', line)
            if agency_id_match:
                agency_id = agency_id_match.group(1)

        elif line.startswith("Agency Name:"):
            agency_name = line.replace("Agency Name:", "").strip()

        elif line.startswith("Agency Details: Main Branch:"):
            address = line.replace("Agency Details: Main Branch:", "").strip()

        elif re.match(r"^\d+$", line):  # Phone number is a standalone number
            phone_number = line.strip()

        else:  # Address continues on new line
            address += " " + line.strip()

    # Append the last agency entry
    if agency_id and agency_name and address and phone_number:
        data.append([agency_id, agency_name, address.strip(), phone_number])

    return data

def save_to_excel(data, output_file):
    df = pd.DataFrame(data, columns=["Agency ID", "Agency Name", "Address", "Phone Number"])
    df.to_excel(output_file, index=False, engine='openpyxl')

if __name__ == "__main__":
    input_file = r"F:\Projects\Data Extraction For Sengaphoreian Gov\Scraper_401_500\agency_details_401_500.txt"  # Change this to your actual file name
    output_file = "agencies5.xlsx"
    agency_data = parse_agency_data(input_file)
    
    if agency_data:
        save_to_excel(agency_data, output_file)
        print(f"Data saved to {output_file}")
    else:
        print("No data extracted. Check the input file format.")
