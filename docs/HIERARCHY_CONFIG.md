## Custom Hierarchy Configuration

### 🎯 **Overview**
The hierarchy upload functionality allows you to create complex multi-level project hierarchies using JSON configuration files. This enables precise control over project structure, collection logic, tags, and SBOM placement.

### 📋 **Configuration Format**

#### Example: hierarchy.json
```json
{
  "meta_app": {
    "version": null,
    "collection_logic": "AGGREGATE_LATEST_VERSION_CHILDREN",
    "classifier": "APPLICATION",
    "tags": ["metapp"],
    "children": [
      {
        "name": "my_app",
        "version": "1.0.0",
        "collection_logic": "AGGREGATE_DIRECT_CHILDREN",
        "classifier": "APPLICATION",
        "tags": ["myapp_version", "myapp"],
        "children": [
          {
            "name": "sub_app",
            "version": "2.0.0",
            "collection_logic": "NONE",
            "classifier": "APPLICATION",
            "tags": ["subtag"],
            "sbom_file": "tests/multiple_sbom/prometheus.json"
          },
          {
            "name": "sub_app2", 
            "version": "2.1.0",
            "collection_logic": "NONE",
            "classifier": "APPLICATION",
            "tags": ["subtag2"],
            "sbom_file": "tests/multiple_sbom/prometheus-operator.json"
          }
        ]
      },
      {
        "name": "my_app",
        "version": "2.0.0",
        "collection_logic": "AGGREGATE_DIRECT_CHILDREN",
        "classifier": "APPLICATION", 
        "tags": ["myapp_version", "myapp"],
        "children": [
          {
            "name": "sub_app",
            "version": "3.0.0",
            "collection_logic": "NONE",
            "classifier": "APPLICATION",
            "tags": ["subtag"],
            "sbom_file": "tests/multiple_sbom/nginx_rpm_1.29.json"
          },
          {
            "name": "sub_app2",
            "version": "3.1.0", 
            "collection_logic": "NONE",
            "classifier": "APPLICATION",
            "tags": ["subtag2"],
            "sbom_file": "tests/single_sbom/nginx_12.9.1.json"
          }
        ]
      }
    ]
  }
}
```

### ⚙️ **Configuration Properties**

| Property | Required | Description | Valid Values |
|----------|----------|-------------|--------------|
| `name` | ✅ | Project name | Any string |
| `version` | ❌ | Project version | Any string or `null` |
| `collection_logic` | ❌ | How children are aggregated | `NONE`, `AGGREGATE_DIRECT_CHILDREN`, `AGGREGATE_DIRECT_CHILDREN_WITH_TAG`, `AGGREGATE_LATEST_VERSION_CHILDREN` |
| `classifier` | ❌ | Project type | `APPLICATION`, `CONTAINER`, `FILE`, etc. |
| `tags` | ❌ | Project tags | Array of strings |
| `sbom_file` | ❌ | Path to SBOM file | Relative path from workspace root |
| `children` | ❌ | Child projects | Array of project objects |

### 🚀 **Usage**

#### Create Hierarchy
```bash
export INPUT_URL="http://localhost:8081"
export INPUT_API_KEY="your-api-key"
export INPUT_PROJECT_HIERARCHY_CONFIG="tests/hierarchy-example.json"
python3 src/main.py upload
```

#### Dry Run
```bash
export INPUT_PROJECT_HIERARCHY_CONFIG="tests/hierarchy-example.json"
export INPUT_DRY_RUN="true"
python3 src/main.py upload
```

#### View Results
You can verify the uploaded projects in the Dependency Track web interface at your configured URL.

### 📊 **Example Output Structure**

```
📁 meta_app (no version)
   🏷️  Classifier: APPLICATION
   ⚙️  Collection Logic: AGGREGATE_LATEST_VERSION_CHILDREN
   └─ 📦 my_app (2.0.0)
   └─ 📦 my_app (1.0.0)

📁 my_app (2.0.0)
   🏷️  Classifier: APPLICATION
   ⚙️  Collection Logic: AGGREGATE_DIRECT_CHILDREN
   └─ 📦 sub_app (3.0.0)
   └─ 📦 sub_app2 (3.1.0)

📁 my_app (1.0.0)
   🏷️  Classifier: APPLICATION
   ⚙️  Collection Logic: AGGREGATE_DIRECT_CHILDREN
   └─ 📦 sub_app (2.0.0)
   └─ 📦 sub_app2 (2.1.0)
```

### ✨ **Key Features**

- **🔄 Recursive Processing**: Unlimited nesting levels
- **🏷️ Tag Support**: Multiple tags per project
- **📦 SBOM Upload**: Automatic SBOM upload to leaf projects
- **🔍 Validation**: Configuration validation and error reporting
- **🧪 Dry Run**: Test configurations before execution
- **🎯 Flexible Structure**: Same project names with different versions
- **⚙️ Collection Logic**: Full control over aggregation behavior

### 🎯 **Use Cases**

1. **Product Releases**: Multiple versions of the same application
2. **Microservices**: Complex service hierarchies
3. **Component Libraries**: Versioned component collections
4. **Environment Separation**: Dev/staging/prod project separation
5. **Team Organization**: Department/team-based project structures

This approach provides complete flexibility for creating any project hierarchy that matches your organization's structure and needs! 🚀
