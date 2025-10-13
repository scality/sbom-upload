# SBOM Upload Action - Architecture Map

## 🏗️ System Architecture

```mermaid
graph TB
    %% External Systems
    subgraph "External Systems"
        GHA[GitHub Actions]
        DT[Dependency Track API]
        SBOM[SBOM Files]
    end

    %% CLI Entry Point
    subgraph "CLI Interface"
        MAIN[main.py]
        CLI[cli/commands.py]
        CLI_CMDS{CLI Commands}
    end

    %% Configuration Layer
    subgraph "Configuration Layer"
        CONFIG[config/config.py]
        INPUTS[config/inputs.py]
        OUTPUTS[config/outputs.py]
        ENV_VARS[Environment Variables]
    end

    %% Domain Layer
    subgraph "Domain Layer"
        MODELS[domain/models.py]
        EXCEPTIONS[domain/exceptions.py]
        VERSION[domain/version.py]
        CONSTANTS[domain/constants.py]
    end

    %% Services Layer
    subgraph "Services Layer"
        CONN_SVC[services/connection.py]
        PROJ_SVC[services/project.py]
        SBOM_SVC[services/sbom.py]
        RESP_HANDLER[services/response_handler.py]
    end

    %% Data Models
    subgraph "Core Models"
        PROJECT_MODEL[Project]
        SBOM_MODEL[SBOMFile]
        UPLOAD_RESULT[UploadResult]
        PROJECT_META[ProjectMetadata]
        HIERARCHY_CONFIG[HierarchyConfig]
    end

    %% Connections
    GHA --> ENV_VARS
    ENV_VARS --> CONFIG
    MAIN --> CLI
    CLI --> CLI_CMDS
    CLI_CMDS --> CONN_SVC
    CLI_CMDS --> PROJ_SVC
    CLI_CMDS --> SBOM_SVC
    
    CONFIG --> MODELS
    MODELS --> PROJECT_MODEL
    MODELS --> SBOM_MODEL
    MODELS --> UPLOAD_RESULT
    MODELS --> PROJECT_META
    MODELS --> HIERARCHY_CONFIG
    
    CONN_SVC --> DT
    CONN_SVC --> RESP_HANDLER
    PROJ_SVC --> CONN_SVC
    PROJ_SVC --> VERSION
    SBOM_SVC --> CONN_SVC
    SBOM_SVC --> PROJ_SVC
    SBOM_SVC --> RESP_HANDLER
    
    SBOM_SVC --> SBOM
    SBOM_MODEL --> SBOM
    
    RESP_HANDLER --> CONSTANTS
    RESP_HANDLER --> EXCEPTIONS

```

## 🔄 Service Dependencies

```mermaid
graph LR
    subgraph "Service Layer Architecture"
        CONN[ConnectionService]
        PROJ[ProjectService]
        SBOM[SBOMService]
        RESP[APIResponseHandler]
    end
    
    subgraph "Dependencies"
        CONN --> RESP
        PROJ --> CONN
        PROJ --> RESP
        SBOM --> CONN
        SBOM --> PROJ
        SBOM --> RESP
    end
    
    subgraph "Domain Dependencies"
        CONN --> CONSTANTS
        PROJ --> VERSION
        SBOM --> MODELS
        RESP --> EXCEPTIONS
    end
```

## 📊 Data Flow

```mermaid
sequenceDiagram
    participant User
    participant CLI
    participant SBOMService
    participant ProjectService
    participant ConnectionService
    participant DependencyTrack

    User->>CLI: upload (with INPUT_PROJECT_SBOM)
    CLI->>SBOMService: upload_single_sbom()
    SBOMService->>SBOMService: load_metadata()
    SBOMService->>ProjectService: create_project()
    ProjectService->>ConnectionService: make_request(POST /project)
    ConnectionService->>DependencyTrack: HTTP Request
    DependencyTrack-->>ConnectionService: Project Created
    ConnectionService-->>ProjectService: Project UUID
    ProjectService-->>SBOMService: Project Object
    SBOMService->>ConnectionService: make_request(POST /bom)
    ConnectionService->>DependencyTrack: Upload SBOM
    DependencyTrack-->>ConnectionService: Upload Success
    ConnectionService-->>SBOMService: Upload Result
    SBOMService-->>CLI: Success Response
    CLI-->>User: Upload Complete
```

## 🎯 CLI Commands Flow

```mermaid
graph TD
    subgraph "CLI Commands"
        TEST[test-connection]
        VALIDATE[validate-inputs]
        UPLOAD[upload - unified command with auto-detection]
    end
    
    subgraph "Service Actions"
        TEST --> CONN_TEST[ConnectionService.test_connection]
        VALIDATE --> CONFIG_VALIDATE[Config.validate_for_upload]
        UPLOAD --> STRATEGY_DETECT[Strategy Pattern - Auto-detect upload mode]
        STRATEGY_DETECT --> SINGLE[SingularUploader]
        STRATEGY_DETECT --> DIRECTORY[DirectoryUploader]
        STRATEGY_DETECT --> LIST[ListUploader]
        STRATEGY_DETECT --> HIERARCHY[NestedUploader]
        SINGLE --> SBOM_UPLOAD[SBOMService.upload_single_sbom]
        UPLOAD_AUTO --> SBOM_UPLOAD
        UPLOAD_NESTED --> SBOM_NESTED[SBOMService.upload_nested_hierarchy]
        UPLOAD_HIERARCHY --> SBOM_HIER[SBOMService.upload_from_hierarchy_config]
        UPLOAD_MAIN --> GITHUB_ACTION[GitHub Action Integration]
        SHOW_HIERARCHY --> PROJ_HIER[ProjectService.get_project_hierarchy]
    end
```

## 🏛️ Clean Architecture Layers

```mermaid
graph TB
    subgraph "Frameworks & Drivers"
        CLI_LAYER[CLI Interface]
        GITHUB_ACTION[GitHub Action]
        HTTP_CLIENT[HTTP Client]
    end
    
    subgraph "Interface Adapters"
        CONFIG_ADAPTER[Configuration Adapter]
        API_ADAPTER[API Response Handler]
        FILE_ADAPTER[File System Adapter]
    end
    
    subgraph "Use Cases"
        UPLOAD_UC[Upload SBOM Use Case]
        PROJECT_UC[Project Management Use Case]
        CONN_UC[Connection Test Use Case]
        VALIDATE_UC[Validation Use Case]
    end
    
    subgraph "Entities"
        PROJECT_ENTITY[Project Entity]
        SBOM_ENTITY[SBOM Entity]
        CONFIG_ENTITY[Configuration Entity]
        RESULT_ENTITY[Result Entity]
    end
    
    CLI_LAYER --> CONFIG_ADAPTER
    GITHUB_ACTION --> CONFIG_ADAPTER
    CONFIG_ADAPTER --> UPLOAD_UC
    CONFIG_ADAPTER --> PROJECT_UC
    CONFIG_ADAPTER --> CONN_UC
    CONFIG_ADAPTER --> VALIDATE_UC
    
    UPLOAD_UC --> PROJECT_ENTITY
    UPLOAD_UC --> SBOM_ENTITY
    PROJECT_UC --> PROJECT_ENTITY
    CONN_UC --> CONFIG_ENTITY
    VALIDATE_UC --> CONFIG_ENTITY
    
    API_ADAPTER --> HTTP_CLIENT
    FILE_ADAPTER --> SBOM_ENTITY
```

## 🔐 Configuration & Environment

```mermaid
graph LR
    subgraph "GitHub Action Inputs"
        ACTION_URL[url]
        ACTION_API_KEY[api-key]
        ACTION_SBOM[project-sbom]
        ACTION_SBOM_LIST[project-sbom-list]
        ACTION_NAME[project_name]
        ACTION_VERSION[project_version]
        ACTION_MORE[... 15+ more inputs]
    end
    
    subgraph "Environment Variables"
        ENV_URL[INPUT_URL]
        ENV_API_KEY[INPUT_API_KEY]
        ENV_SBOM[INPUT_PROJECT_SBOM]
        ENV_SBOM_LIST[INPUT_PROJECT_SBOM_LIST]
        ENV_NAME[INPUT_PROJECT_NAME]
        ENV_VERSION[INPUT_PROJECT_VERSION]
        ENV_MORE[... ENV variables]
    end
    
    subgraph "AppConfig"
        CONFIG_OBJ[AppConfig Object]
        VALIDATION[Configuration Validation]
        NORMALIZATION[Data Normalization]
    end
    
    ACTION_URL --> ENV_URL
    ACTION_API_KEY --> ENV_API_KEY
    ACTION_SBOM --> ENV_SBOM
    ACTION_SBOM_LIST --> ENV_SBOM_LIST
    ACTION_NAME --> ENV_NAME
    ACTION_VERSION --> ENV_VERSION
    ACTION_MORE --> ENV_MORE
    
    ENV_URL --> CONFIG_OBJ
    ENV_API_KEY --> CONFIG_OBJ
    ENV_SBOM --> CONFIG_OBJ
    ENV_SBOM_LIST --> CONFIG_OBJ
    ENV_NAME --> CONFIG_OBJ
    ENV_VERSION --> CONFIG_OBJ
    ENV_MORE --> CONFIG_OBJ
    
    CONFIG_OBJ --> VALIDATION
    CONFIG_OBJ --> NORMALIZATION
```

## 🎯 Upload Scenarios

```mermaid
graph TD
    subgraph "Upload Types"
        SINGLE[Single SBOM Upload]
        MULTIPLE[Multiple SBOM Upload]
        NESTED[Nested Hierarchy Upload]
        CUSTOM[Custom Hierarchy Upload]
    end
    
    subgraph "Single SBOM Flow"
        SINGLE --> EXTRACT_META[Extract Metadata]
        EXTRACT_META --> CREATE_PROJ[Create/Find Project]
        CREATE_PROJ --> UPLOAD_SBOM[Upload SBOM File]
        UPLOAD_SBOM --> UPDATE_LATEST[Update Latest Flag]
    end
    
    subgraph "Multiple SBOM Flow"
        MULTIPLE --> ITERATE[Iterate SBOM Files]
        ITERATE --> SINGLE
    end
    
    subgraph "Nested Flow"
        NESTED --> CREATE_PARENT[Create Parent Project]
        CREATE_PARENT --> FIND_SBOMS[Find SBOM Files]
        FIND_SBOMS --> CREATE_CHILDREN[Create Child Projects]
        CREATE_CHILDREN --> UPLOAD_TO_CHILDREN[Upload SBOMs to Children]
    end
    
    subgraph "Custom Hierarchy Flow"
        CUSTOM --> PARSE_CONFIG[Parse JSON/YAML Config]
        PARSE_CONFIG --> RECURSIVE_PROCESS[Recursive Project Processing]
        RECURSIVE_PROCESS --> CREATE_HIERARCHY[Create Project Hierarchy]
        CREATE_HIERARCHY --> UPLOAD_SBOMS[Upload Associated SBOMs]
    end
```

## 📦 File Structure Overview

```mermaid
graph TD
    subgraph "Project Structure"
        ROOT[sbom-upload/]
        SRC[src/]
        DOCS[docs/]
        TESTS[tests/]
        ACTION[action.yaml]
        README[README.md]
    end
    
    subgraph "Source Code"
        SRC --> CLI_DIR[cli/]
        SRC --> CONFIG_DIR[config/]
        SRC --> DOMAIN_DIR[domain/]
        SRC --> SERVICES_DIR[services/]
        SRC --> MAIN_PY[main.py]
    end
    
    subgraph "Documentation"
        DOCS --> USAGE[USAGE_EXAMPLES.md]
        DOCS --> QUICKSTART[QUICKSTART.md]
        DOCS --> CLI_DOC[CLI.md]
        DOCS --> HIERARCHY[HIERARCHY_CONFIG.md]
        DOCS --> WORKFLOW[PRE_MERGE_WORKFLOW.md]
    end
    
    subgraph "Test Files"
        TESTS --> SINGLE_SBOM[single_sbom/]
        TESTS --> MULTIPLE_SBOM[multiple_sbom/]
        TESTS --> HIERARCHY_EXAMPLE[hierarchy-example.json]
        TESTS --> DOCKER[docker/]
        TESTS --> TEST_SCRIPTS[test scripts]
    end
```