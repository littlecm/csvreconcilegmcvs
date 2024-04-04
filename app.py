import streamlit as st
import pandas as pd
import requests
from io import StringIO

def load_csv(source):
    if source.startswith('http'):
        # Load CSV from URL
        content = requests.get(source).content
        df = pd.read_csv(StringIO(content.decode('utf-8')))
    else:
        # Load CSV from uploaded file
        df = pd.read_csv(source)
    return df

def process_vins(vins, source_name, headers):
    results = []
    for vin in vins:
        api_url = f"https://cws.gm.com/vs-cws/vehshop/v2/vehicle?vin={vin}&postalCode=48640&locale=en_US"
        api_response = requests.get(api_url, headers=headers)

        if api_response.ok:
            api_data = api_response.json()

            if "mathBox" in api_data and "recallInfo" in api_data["mathBox"] and "This vehicle is temporarily unavailable" in api_data["mathBox"]["recallInfo"]:
                results.append({'VIN': vin, 'Result': "Vehicle with Recall"})
            elif "inventoryStatus" in api_data:
                inventory_status = api_data["inventoryStatus"].get("name", "")
                if inventory_status == "Rtl_Intrans":
                    results.append({'VIN': vin, 'Result': "In Transit - Not expected in Vinsolutions"})
                elif inventory_status == "EligRtlStkCT":
                    results.append({'VIN': vin, 'Result': "Courtesy Vehicle"})
                else:
                    results.append({'VIN': vin, 'Result': f"Other Inventory Status: {inventory_status}"})
            else:
                results.append({'VIN': vin, 'Result': f"Exclusive to {source_name}"})
        else:
            results.append({'VIN': vin, 'Result': "API request failed"})
    
    return pd.DataFrame(results)

# Streamlit app
st.title('VIN Reconciliation App')

st.header('Provide CSV File Sources')
st.write('Enter the URLs for the CSV files or manually upload them.')

# Input for CSV file URLs or Upload
col1, col2 = st.columns(2)

with col1:
    st.write("DI CSV Source")
    di_url = st.text_input("Enter DI CSV URL:", "")
    di_upload = st.file_uploader("Or upload DI CSV file:", type='csv', key="di_upload")

with col2:
    st.write("Homenet CSV Source")
    homenet_url = st.text_input("Enter Homenet CSV URL:", "")
    homenet_upload = st.file_uploader("Or upload Homenet CSV file:", type='csv', key="homenet_upload")

# Load CSV files based on input method
if di_url or di_upload:
    di_source = di_url if di_url else di_upload
    di_df = load_csv(di_source)

if homenet_url or homenet_upload:
    homenet_source = homenet_url if homenet_url else homenet_upload
    homenet_df = load_csv(homenet_source)

if 'di_df' in locals() and 'homenet_df' in locals():
    vin_in_di_not_homenet = set(di_df['VIN']) - set(homenet_df['VIN'])
    vin_in_homenet_not_di = set(homenet_df['VIN']) - set(di_df['VIN'])

    if st.button('Reconcile VINs'):
        headers = {'Authorization': 'Bearer your_access_token'}  # Replace 'your_access_token' with your actual token
        results_di = process_vins(vin_in_di_not_homenet, 'DI', headers)
        results_homenet = process_vins(vin_in_homenet_not_di, 'Homenet', headers)

        st.subheader('Results for VINs unique to DI CSV')
        st.write(results_di)

        st.subheader('Results for VINs unique to Homenet CSV')
        st.write(results_homenet)

        # Optional: Download results as CSV
        st.download_button(label='Download DI Results', data=results_di.to_csv(index=False), file_name='di_results.csv', mime='text/csv')
        st.download_button(label='Download Homenet Results', data=results_homenet.to_csv(index=False), file_name='homenet_results.csv', mime='text/csv')
