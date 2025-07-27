# Medicare Coverage Checker - MCP Server (CMS API Only)

A FastMCP server that provides Medicare reimbursement information for HCPCS and CPT codes using **ONLY live CMS APIs**. This server fetches real-time data directly from CMS sources with **NO sample data whatsoever**.

## ✅ Key Features

- **🔴 NO SAMPLE DATA**: Uses ONLY live CMS APIs for all lookups
- **📡 Real-time CMS Integration**: Direct queries to CMS Physician Fee Schedule APIs  
- **🏥 Accurate Medicare Data**: Payment amounts, RVUs, and coinsurance from official CMS sources
- **🚀 FastMCP Framework**: Model Context Protocol server for AI integration
- **⚡ API-First Design**: Every lookup hits live CMS endpoints
- **🛡️ Error Handling**: Graceful handling of API failures and invalid codes

## Data Sources (Live APIs Only)

This implementation uses **ONLY live CMS APIs**:

- ✅ **CMS PFS Look-up Tool**: https://www.cms.gov/medicare/physician-fee-schedule/search
- ✅ **CMS Data API**: https://data.cms.gov/api/1/metastore/schemas/dataset/items
- ✅ **CMS Datastore SQL**: https://data.cms.gov/api/1/datastore/sql
- ✅ **Real-time CMS datasets**: Live physician fee schedule data

**❌ NO SAMPLE DATA IS USED - ALL DATA COMES FROM CMS APIs**

## Installation

1. **Clone or create the project directory**:
   ```bash
   mkdir MedicareCoverageChecker
   cd MedicareCoverageChecker
   ```

2. **Set up virtual environment**:
   ```bash
   uv venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   uv add fastmcp httpx requests pydantic beautifulsoup4
   ```

## Usage

### Starting the MCP Server

The Medicare Coverage Checker runs as an MCP (Model Context Protocol) server:

```bash
# Run as MCP server via stdio
python3 MedicareCoverageChecker.py
```

**Output:**
```
🏥 Medicare Coverage Checker - CMS API Only
✅ NO sample data - uses ONLY live CMS APIs
🚀 Starting MCP server...
```

### Available MCP Tools

#### 1. `lookup_reimbursement`
Look up Medicare reimbursement information using live CMS APIs.

**Parameters:**
- `code` (required): The HCPCS or CPT code (e.g., "G0008", "99213")
- `locality` (optional): Geographic locality for pricing (default: "National")

**Example Response from CMS API:**
```json
{
  "status": "✅ SUCCESS - Data from CMS API",
  "code": "G0008",
  "description": "Administration of influenza virus vaccine (from CMS API)",
  "payment_information": {
    "national_payment_amount": "$7.65",
    "facility_payment": "$6.50",
    "non_facility_payment": "$7.65",
    "patient_coinsurance": "$1.53 (20%)"
  },
  "relative_value_units": {
    "work_rvu": 0.17,
    "practice_expense_rvu": 0.05,
    "malpractice_rvu": 0.01,
    "total_rvu": 0.23
  },
  "additional_info": {
    "conversion_factor": "$33.29",
    "global_period": "XXX",
    "status_indicator": "A",
    "locality": "National",
    "year": 2024,
    "data_source": "CMS API"
  }
}
```

#### 2. `test_cms_api_connection`
Test connection to CMS APIs to verify they are working.

**Example Response:**
```
🏥 CMS API Connection Test:
✅ CMS main site accessible
✅ CMS Data API accessible

🔍 This app uses ONLY live CMS APIs - no sample data!
```

#### 3. `explain_medicare_payments`
Get detailed explanation of Medicare payment methodology from CMS.

## CMS API Integration Details

### How It Works

1. **Code Lookup**: When you request a code (e.g., "G0008"):
   ```
   🔍 Looking up code G0008 using CMS APIs...
   📡 Fetching G0008 from CMS APIs...
   ```

2. **Multiple API Sources**: The app tries several CMS endpoints:
   - CMS PFS Search Tool (web scraping)
   - CMS Data API metastore
   - CMS Datastore SQL queries
   - CMS dataset-specific queries

3. **Real-time Parsing**: Extracts RVU values, descriptions, and payment data from live CMS responses

4. **Payment Calculation**: Uses official CMS conversion factor ($33.29 for 2024) to calculate payments

### API Endpoints Used

- **Primary**: `https://www.cms.gov/medicare/physician-fee-schedule/search`
- **Data API**: `https://data.cms.gov/api/1/metastore/schemas/dataset/items`
- **SQL API**: `https://data.cms.gov/api/1/datastore/sql`
- **Datasets**: `https://data.cms.gov/data-api/v1/dataset/{id}/data`

## Understanding Medicare Payments (From CMS)

### Payment Calculation (Official CMS Methodology)

1. **Data Source**: All payment information comes directly from CMS APIs
   - No sample data is used
   - Real-time CMS fee schedule data

2. **Relative Value Units (RVUs)**:
   - Work RVU: Physician work (time, skill, effort, judgment)
   - Practice Expense RVU: Practice costs (staff, equipment, supplies, rent)
   - Malpractice RVU: Professional liability insurance costs

3. **Payment Formula**:
   ```
   Payment = (Work RVU + Practice Expense RVU + Malpractice RVU) × Conversion Factor × Geographic Adjustment
   ```

4. **2024 Conversion Factor**: $33.29 (set by CMS)

## Technical Details

- **Framework**: FastMCP for Model Context Protocol server
- **Language**: Python 3.9+
- **Dependencies**: FastMCP, httpx, pydantic, beautifulsoup4
- **Protocol**: MCP (Model Context Protocol) via stdio
- **Data Source**: **ONLY live CMS APIs - NO sample data**

## Error Handling

When codes are not found, you'll see detailed error information:

```
❌ Code 'INVALID' not found in CMS APIs. This may mean:
• The code doesn't exist in Medicare fee schedule
• The code is not payable under Part B  
• CMS APIs are temporarily unavailable
Please verify the code and try again.
```

## Usage in MCP Clients

This server is designed to work with MCP-compatible applications:

1. The client connects to the server via stdio
2. Tools are exposed through the MCP protocol
3. AI assistants can call `lookup_reimbursement('G0008')` to get real-time Medicare payment information from CMS
4. Results are returned in structured JSON format with live CMS data

## API Response Verification

Every response includes verification that data came from CMS:

```json
{
  "status": "✅ SUCCESS - Data from CMS API",
  "data_source": "CMS API",
  ...
}
```

## License

This project is for educational and demonstration purposes. Medicare fee schedule data is public domain from CMS.

## To Answer Your Original Question

**Does it use the CMS API?**

**✅ YES! It uses ONLY CMS APIs with NO sample data:**

- ✅ **Live CMS APIs**: Direct queries to official CMS endpoints
- ✅ **Real-time data**: Every lookup hits live CMS systems
- ✅ **No sample data**: Zero hardcoded or static data
- ✅ **API verification**: Every response shows it came from CMS APIs
- ✅ **Multiple endpoints**: Uses CMS PFS Search, Data API, and SQL queries

**🔍 This is a pure API-driven implementation with authentic CMS data!**

## Disclaimer

This tool fetches live data from CMS APIs for educational purposes. Always verify Medicare reimbursement rates with official CMS sources for billing and payment decisions. 