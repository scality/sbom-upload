#!/usr/bin/env python3
import requests

base_url = 'http://localhost:8081/api/v1'
api_key = 'odt_8meYY3nC_K7gUnjWS1K7VpF2SzfbW68Da0ZZzy6gY'
headers = {
    'Accept': 'application/json',
    'Content-Type': 'application/json',
    'X-API-Key': api_key
}

def get_all_root_projects():
    """Get all root projects (projects without parents)"""
    url = f"{base_url}/project"
    params = {
        'pageNumber': 1,
        'pageSize': 100,
        'sortOrder': 'asc,desc',
        'onlyRoot': True
    }
    
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        return response.json()
    print(f"Error fetching projects: {response.status_code} - {response.text}")
    return []

def delete_project(project_uuid):
    """Delete a project by UUID"""
    url = f"{base_url}/project/{project_uuid}"
    delete_headers = {
        'Accept': '*/*',
        'X-API-Key': api_key
    }
    
    response = requests.delete(url, headers=delete_headers)
    return response.status_code


def delete_all_projects():
    """Delete all root projects"""
    print("Deleting all projects")
    
    projects = get_all_root_projects()
    for project in projects:
        project_uuid = project['uuid']
        project_name = project.get('name', 'Unknown')
        print(f"  Deleting project: {project_name} (UUID: {project_uuid})")
        
        status_code = delete_project(project_uuid)
        if status_code == 204:
            print(f"    Successfully deleted")
        else:
            print(f"    Error deleting: Status {status_code}")


def main():
    """Main function to reset Dependency Track projects"""
    print("Starting Dependency Track reset...")
    
    # Delete all existing projects
    delete_all_projects()
    
    print("\nReset completed!")

if __name__ == "__main__":
    main()
