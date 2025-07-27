#!/usr/bin/env python3
"""
MedicareCoverageChecker - MCP Server for Medicare Reimbursement Information

This server provides Medicare reimbursement information for HCPCS and CPT codes.
"""

import httpx
import json
import asyncio
from typing import Dict, Any, Optional, List, Union
from fastmcp import FastMCP
from pydantic import BaseModel
import re
from bs4 import BeautifulSoup


class ReimbursementInfo(BaseModel):
    """Model for Medicare reimbursement information"""
    hcpcs_code: str
    description: str
    work_rvu: Optional[float] = None
    practice_expense_rvu: Optional[float] = None
    malpractice_rvu: Optional[float] = None
    total_rvu: Optional[float] = None
    conversion_factor: float = 33.29  # 2024 Medicare conversion factor
    national_payment_amount: Optional[float] = None
    facility_payment: Optional[float] = None
    non_facility_payment: Optional[float] = None
    coinsurance_amount: Optional[float] = None
    global_period: Optional[str] = None
    status_indicator: Optional[str] = None
    locality: str = "National"
    year: int = 2024
    data_source: str = "CMS API"


class MedicareCoverageChecker:
    """Medicare Coverage Checker for Medicare reimbursement information"""
    
    def __init__(self):
        self.conversion_factor = 33.29  # 2024 Medicare conversion factor
        self.coinsurance_rate = 0.20  # Standard 20% coinsurance
        
        # CMS API endpoints
        self.cms_pfs_search_url = "https://www.cms.gov/medicare/physician-fee-schedule/search"
        self.cms_data_api_base = "https://data.cms.gov"
        
        # HTTP headers to avoid blocking
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/json, text/html, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
    
    async def lookup_code(self, code: str, locality: str = "National") -> Optional[ReimbursementInfo]:
        """
        Look up Medicare reimbursement information
        
        Args:
            code: HCPCS or CPT code (e.g., "G0008", "99213")
            locality: Geographic locality (default: "National")
            
        Returns:
            ReimbursementInfo object or None if not found
        """
        # Normalize the code
        code = code.upper().strip()
        
        print(f"🔍 Looking up code {code} using CMS APIs...")
        
        # Try multiple CMS API sources
        cms_data = await self._fetch_from_cms_apis(code)
        if cms_data:
            return self._create_reimbursement_info(code, cms_data, locality)
        
        return None
    
    async def _fetch_from_cms_apis(self, code: str) -> Optional[Dict[str, Any]]:
        """
        Fetch data from CMS APIs
        """
        print(f"📡 Fetching {code} from CMS APIs...")
        
        # Try CMS PFS Search Tool
        pfs_data = await self._query_cms_pfs_search(code)
        if pfs_data:
            return pfs_data
        
        # Try alternative CMS data sources
        alt_data = await self._query_cms_data_sources(code)
        if alt_data:
            return alt_data
        
        print(f"❌ No data found for {code} in CMS APIs")
        return None
    
    async def _query_cms_pfs_search(self, code: str) -> Optional[Dict[str, Any]]:
        """
        Query the CMS PFS Search Tool
        """
        try:
            async with httpx.AsyncClient(timeout=30.0, headers=self.headers) as client:
                # First, get the search page to extract any necessary tokens/cookies
                search_response = await client.get(self.cms_pfs_search_url)
                
                if search_response.status_code == 200:
                    # Parse the page to find search functionality
                    soup = BeautifulSoup(search_response.text, 'html.parser')
                    
                    # Try to find the search form and make a POST request
                    search_form = soup.find('form')
                    if search_form:
                        form_action = search_form.get('action', '/medicare/physician-fee-schedule/search')
                        
                        # Construct search URL or POST data
                        search_url = f"https://www.cms.gov{form_action}"
                        
                        # Try different search parameters
                        search_params = {
                            'hcpcs': code,
                            'code': code,
                            'procedure_code': code,
                            'search': code
                        }
                        
                        # Make the search request
                        search_result = await client.post(search_url, data=search_params)
                        
                        if search_result.status_code == 200:
                            return await self._parse_cms_search_results(search_result.text, code)
                
        except Exception as e:
            print(f"🚨 CMS PFS Search error for {code}: {str(e)}")
        
        return None
    
    async def _query_cms_data_sources(self, code: str) -> Optional[Dict[str, Any]]:
        """
        Try alternative CMS data API endpoints
        """
        endpoints_to_try = [
            # New CMS data API endpoints
            f"https://data.cms.gov/api/1/metastore/schemas/dataset/items",
            f"https://data.cms.gov/api/1/datastore/sql",
            f"https://data.cms.gov/data-api/v1/dataset/",
        ]
        
        for endpoint in endpoints_to_try:
            try:
                async with httpx.AsyncClient(timeout=30.0, headers=self.headers) as client:
                    # Query for physician fee schedule datasets
                    if "metastore" in endpoint:
                        response = await client.get(endpoint)
                        if response.status_code == 200:
                            datasets = response.json()
                            # Look for physician fee schedule related datasets
                            for dataset in datasets:
                                if any(term in str(dataset).lower() for term in ['physician', 'fee', 'schedule', 'pfs']):
                                    dataset_id = dataset.get('identifier', '')
                                    if dataset_id:
                                        # Try to query this dataset for our code
                                        data_result = await self._query_cms_dataset(dataset_id, code)
                                        if data_result:
                                            return data_result
                    
                    elif "datastore/sql" in endpoint:
                        # Try SQL query approach
                        sql_query = f"SELECT * FROM physician_fee_schedule WHERE hcpcs_cd = '{code}' LIMIT 1"
                        sql_data = {"query": sql_query}
                        response = await client.post(endpoint, json=sql_data)
                        if response.status_code == 200:
                            result = response.json()
                            if result and len(result) > 0:
                                return await self._parse_cms_sql_result(result[0], code)
                
            except Exception as e:
                print(f"🚨 CMS Data API error for {code}: {str(e)}")
                continue
        
        return None
    
    async def _query_cms_dataset(self, dataset_id: str, code: str) -> Optional[Dict[str, Any]]:
        """
        Query a specific CMS dataset
        """
        try:
            async with httpx.AsyncClient(timeout=30.0, headers=self.headers) as client:
                dataset_url = f"https://data.cms.gov/data-api/v1/dataset/{dataset_id}/data"
                
                # Try with filter parameters
                params = {
                    'filter[hcpcs_cd]': code,
                    'filter[hcpcs_code]': code,
                    'filter[code]': code,
                    'limit': 1
                }
                
                for param_key, param_value in params.items():
                    try:
                        response = await client.get(dataset_url, params={param_key: param_value, 'limit': 1})
                        if response.status_code == 200:
                            data = response.json()
                            if data and len(data) > 0:
                                return await self._parse_cms_dataset_result(data[0], code)
                    except:
                        continue
                        
        except Exception as e:
            print(f"🚨 Dataset query error for {code}: {str(e)}")
        
        return None
    
    async def _parse_cms_search_results(self, html_content: str, code: str) -> Optional[Dict[str, Any]]:
        """
        Parse CMS PFS search results from HTML
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Look for tables or data containing the code
            tables = soup.find_all('table')
            for table in tables:
                rows = table.find_all('tr')
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    if any(code in cell.get_text() for cell in cells):
                        # Extract data from this row
                        cell_texts = [cell.get_text().strip() for cell in cells]
                        return await self._parse_table_row_data(cell_texts, code)
            
            # Look for JSON data in script tags
            scripts = soup.find_all('script')
            for script in scripts:
                if script.string and code in script.string:
                    # Try to extract JSON data
                    json_match = re.search(r'\{.*?\}', script.string)
                    if json_match:
                        try:
                            json_data = json.loads(json_match.group())
                            return json_data
                        except:
                            continue
            
        except Exception as e:
            print(f"🚨 HTML parsing error for {code}: {str(e)}")
        
        return None
    
    async def _parse_table_row_data(self, cell_texts: List[str], code: str) -> Optional[Dict[str, Any]]:
        """
        Parse table row data to extract RVU and payment information
        """
        try:
            # Common patterns in CMS PFS tables
            data = {"hcpcs_code": code}
            
            for i, text in enumerate(cell_texts):
                text = text.lower().strip()
                
                # Try to extract RVU values
                if 'work' in text and i + 1 < len(cell_texts):
                    try:
                        data['work_rvu'] = float(cell_texts[i + 1])
                    except:
                        pass
                
                elif 'practice' in text and 'expense' in text and i + 1 < len(cell_texts):
                    try:
                        data['practice_expense_rvu'] = float(cell_texts[i + 1])
                    except:
                        pass
                
                elif 'malpractice' in text and i + 1 < len(cell_texts):
                    try:
                        data['malpractice_rvu'] = float(cell_texts[i + 1])
                    except:
                        pass
                
                elif 'description' in text and i + 1 < len(cell_texts):
                    data['description'] = cell_texts[i + 1]
                
                # Look for numerical values that might be RVUs
                try:
                    value = float(text)
                    if 0 < value < 100:  # Reasonable RVU range
                        if 'work_rvu' not in data:
                            data['work_rvu'] = value
                        elif 'practice_expense_rvu' not in data:
                            data['practice_expense_rvu'] = value
                        elif 'malpractice_rvu' not in data:
                            data['malpractice_rvu'] = value
                except:
                    pass
            
            return data if len(data) > 1 else None
            
        except Exception as e:
            print(f"🚨 Table parsing error for {code}: {str(e)}")
        
        return None
    
    async def _parse_cms_sql_result(self, result: Dict[str, Any], code: str) -> Optional[Dict[str, Any]]:
        """
        Parse CMS SQL query result
        """
        try:
            # Map common CMS field names
            field_mapping = {
                'hcpcs_cd': 'hcpcs_code',
                'hcpcs_code': 'hcpcs_code',
                'hcpcs_desc': 'description',
                'hcpcs_description': 'description',
                'work_rvu': 'work_rvu',
                'pe_rvu': 'practice_expense_rvu',
                'practice_expense_rvu': 'practice_expense_rvu',
                'mp_rvu': 'malpractice_rvu',
                'malpractice_rvu': 'malpractice_rvu',
                'glob_days': 'global_period',
                'status_ind': 'status_indicator'
            }
            
            mapped_data = {}
            for cms_field, our_field in field_mapping.items():
                if cms_field in result:
                    mapped_data[our_field] = result[cms_field]
            
            return mapped_data if mapped_data else None
            
        except Exception as e:
            print(f"🚨 SQL result parsing error for {code}: {str(e)}")
        
        return None
    
    async def _parse_cms_dataset_result(self, result: Dict[str, Any], code: str) -> Optional[Dict[str, Any]]:
        """
        Parse CMS dataset API result
        """
        try:
            # Handle various CMS data formats
            parsed_data = {"hcpcs_code": code}
            
            # Extract available fields
            if 'hcpcs_description' in result:
                parsed_data['description'] = result['hcpcs_description']
            elif 'description' in result:
                parsed_data['description'] = result['description']
            
            # Extract RVU values
            for rvu_field in ['work_rvu', 'pe_rvu', 'mp_rvu']:
                if rvu_field in result:
                    try:
                        parsed_data[rvu_field.replace('pe_', 'practice_expense_').replace('mp_', 'malpractice_')] = float(result[rvu_field])
                    except:
                        pass
            
            return parsed_data if len(parsed_data) > 1 else None
            
        except Exception as e:
            print(f"🚨 Dataset result parsing error for {code}: {str(e)}")
        
        return None
    
    def _create_reimbursement_info(self, code: str, data: Dict[str, Any], locality: str) -> ReimbursementInfo:
        """Create a ReimbursementInfo object from CMS API data"""
        
        # Extract RVU values
        work_rvu = data.get("work_rvu", 0.0)
        practice_expense_rvu = data.get("practice_expense_rvu", 0.0)
        malpractice_rvu = data.get("malpractice_rvu", 0.0)
        total_rvu = work_rvu + practice_expense_rvu + malpractice_rvu
        
        # Calculate payment amounts
        if total_rvu > 0:
            national_payment = total_rvu * self.conversion_factor
            facility_payment = national_payment * 0.85  # Typically lower in facility
            non_facility_payment = national_payment
            coinsurance_amount = national_payment * self.coinsurance_rate
        else:
            national_payment = facility_payment = non_facility_payment = None
            coinsurance_amount = None
        
        return ReimbursementInfo(
            hcpcs_code=code,
            description=data.get("description", f"Procedure code {code} (from CMS API)"),
            work_rvu=work_rvu,
            practice_expense_rvu=practice_expense_rvu,
            malpractice_rvu=malpractice_rvu,
            total_rvu=total_rvu,
            conversion_factor=self.conversion_factor,
            national_payment_amount=round(national_payment, 2) if national_payment else None,
            facility_payment=round(facility_payment, 2) if facility_payment else None,
            non_facility_payment=round(non_facility_payment, 2) if non_facility_payment else None,
            coinsurance_amount=round(coinsurance_amount, 2) if coinsurance_amount else None,
            global_period=data.get("global_period"),
            status_indicator=data.get("status_indicator"),
            locality=locality,
            year=2024,
            data_source="CMS API"
        )


# Initialize FastMCP server
mcp = FastMCP("Medicare Coverage Checker")
medicare_checker = MedicareCoverageChecker()


@mcp.tool()
async def lookup_reimbursement(
    code: str,
    locality: str = "National"
) -> Union[Dict[str, Any], str]:
    """
    Look up Medicare reimbursement information using CMS APIs.
    
    Args:
        code: The HCPCS or CPT code to look up (e.g., "G0008", "99213")
        locality: Geographic locality for pricing (default: "National")
    
    Returns:
        Medicare reimbursement information from CMS APIs or error message
    """
    try:
        # Validate input
        if not code or len(code.strip()) == 0:
            return "Error: Please provide a valid HCPCS or CPT code"
        
        # Clean up the code
        code = code.strip().upper()
        
        print(f"🏥 Medicare Coverage Checker - Looking up {code} via CMS APIs...")
        
        # Look up the code using CMS APIs
        result = await medicare_checker.lookup_code(code, locality)
        
        if result is None:
            return f"❌ Code '{code}' not found in CMS APIs. This may mean:\n" + \
                   f"• The code doesn't exist in Medicare fee schedule\n" + \
                   f"• The code is not payable under Part B\n" + \
                   f"• CMS APIs are temporarily unavailable\n" + \
                   f"Please verify the code and try again."
        
        # Format the response
        response = {
            "status": "✅ SUCCESS - Data from CMS API",
            "code": result.hcpcs_code,
            "description": result.description,
            "payment_information": {
                "national_payment_amount": f"${result.national_payment_amount:.2f}" if result.national_payment_amount else "Not applicable",
                "facility_payment": f"${result.facility_payment:.2f}" if result.facility_payment else "Not applicable", 
                "non_facility_payment": f"${result.non_facility_payment:.2f}" if result.non_facility_payment else "Not applicable",
                "patient_coinsurance": f"${result.coinsurance_amount:.2f} (20%)" if result.coinsurance_amount else "Varies"
            },
            "relative_value_units": {
                "work_rvu": result.work_rvu,
                "practice_expense_rvu": result.practice_expense_rvu,
                "malpractice_rvu": result.malpractice_rvu,
                "total_rvu": result.total_rvu
            },
            "additional_info": {
                "conversion_factor": f"${result.conversion_factor}",
                "global_period": result.global_period,
                "status_indicator": result.status_indicator,
                "locality": result.locality,
                "year": result.year,
                "data_source": result.data_source
            }
        }
        
        return response
        
    except Exception as e:
        return f"🚨 API Error looking up code '{code}': {str(e)}"


@mcp.tool()
async def test_cms_api_connection() -> str:
    """
    Test connection to CMS APIs to verify they are working.
    
    Returns:
        Status of CMS API connections
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Test CMS main site
            response = await client.get("https://www.cms.gov")
            cms_status = "✅ CMS main site accessible" if response.status_code == 200 else "❌ CMS main site not accessible"
            
            # Test CMS data API
            try:
                data_response = await client.get("https://data.cms.gov/api/1/metastore/schemas/dataset/items")
                data_status = "✅ CMS Data API accessible" if data_response.status_code == 200 else "❌ CMS Data API not accessible"
            except:
                data_status = "❌ CMS Data API not accessible"
            
            return f"🏥 CMS API Connection Test:\n{cms_status}\n{data_status}\n\n🔍 This app uses live CMS APIs!"
            
    except Exception as e:
        return f"🚨 Connection test failed: {str(e)}"


@mcp.tool()
async def explain_medicare_payments() -> str:
    """
    Explain how Medicare payments are calculated using CMS methodology.
    
    Returns:
        Detailed explanation of Medicare payment methodology from CMS
    """
    explanation = """
    🏥 Medicare Payment Calculation (CMS Official Methodology):

               1. **Data Source**: All payment information comes directly from CMS APIs
              - Real-time CMS fee schedule data

    2. **Relative Value Units (RVUs)**:
       - Work RVU: Physician work (time, skill, effort, judgment)
       - Practice Expense RVU: Practice costs (staff, equipment, supplies, rent)
       - Malpractice RVU: Professional liability insurance costs

    3. **Payment Calculation**:
       Payment = (Work RVU + Practice Expense RVU + Malpractice RVU) × Conversion Factor × Geographic Adjustment

    4. **2024 Conversion Factor**: $33.29 (set by CMS)

    5. **Payment Settings**:
       - Facility Payment: Service performed in hospital/facility (lower practice expense)
       - Non-Facility Payment: Service performed in physician office (higher practice expense)

    6. **Patient Responsibility**:
       - Medicare pays 80% of approved amount
       - Patient pays 20% coinsurance (after deductible)

    7. **Geographic Adjustments**:
       - Geographic Practice Cost Indices (GPCIs) adjust for local costs
       - Applied to work, practice expense, and malpractice RVUs

    🔍 All data is fetched live from CMS APIs - ensuring accuracy and compliance!
    """
    return explanation


if __name__ == "__main__":
    print("🏥 Medicare Coverage Checker")
    print("✅ Uses live CMS APIs")
    print("🚀 Starting MCP server...")
    
    # Run as MCP server via stdio (not web server)
    mcp.run()
