# Architecture Diagram

## System Overview

```mermaid
graph TD
    A[Input Sources] --> B[Loaders]
    B --> C[RDF Triplestore]
    C --> D[NMA Vocabulary Creation]
    D --> E[Fixture Generation]
    E --> F[Output Files]
    
    A1[CSV Files<br/>CCMM_slovniky*.csv] --> B
    A2[SPARQL Endpoints<br/>RDF Files] --> B
    A3[YAML Files<br/>licenses.yaml, subject_schemes.yaml] --> B
    A4[SSSOM Mappings<br/>*.tsv] --> B
    
    B1[CSVToRDFLoader] --> C
    B2[SPARQLLoader] --> C
    B3[YAMLToRDFLoader] --> C
    B4[SSSOMLoader] --> C
    
    C --> D1[create_nma_vocabulary_terms]
    D1 --> D2[Create NMA concepts from external schemes]
    D2 --> D3[_create_contributors_roles]
    
    D --> E1[FixtureGenerator]
    E1 --> E2[generate_all]
    E2 --> E3[_generate_ccmm_vocabulary]
    E2 --> E4[_generate_ccmm_vocabulary_with_sorting]
    E2 --> E5[_generate_contributor_types]
    E2 --> E6[_generate_rdm_subjects]
    
    E --> F1[YAML Fixtures<br/>ccmm_*.yaml]
    E --> F2[vocabularies.ttl<br/>Sorted Turtle]
    
    style A fill:#e1f5ff
    style B fill:#fff4e1
    style C fill:#e8f5e9
    style D fill:#fff9c4
    style E fill:#f3e5f5
    style F fill:#fce4ec
```

## Data Flow

```mermaid
flowchart LR
    subgraph Input["📁 Input Data"]
        CSV[CSV Files<br/>CCMM_slovniky*.csv]
        RDF[RDF Sources<br/>COAR NT files, EU Publications]
        YAML[YAML Files<br/>licenses.yaml, subject_schemes.yaml]
        SSSOM[SSSOM Files<br/>Mappings *.tsv]
    end
    
    subgraph Loading["⚙️ Loading Phase"]
        Store[RDF Triplestore<br/>RDFTripleStore]
        
        CSV --> |CSVToRDFLoader| Store
        RDF --> |SPARQLLoader| Store
        YAML --> |YAMLToRDFLoader| Store
        SSSOM --> |SSSOMLoader| Store
    end
    
    subgraph Transformation["🔄 Transformation Phase"]
        NMACreate[create_nma_vocabulary_terms]
        NMACreate --> |Transform external→NMA| NMAConcepts[NMA Concepts<br/>with skos:exactMatch]
        ContributorCreate[_create_contributors_roles]
        ContributorCreate --> |Create subset| ContributorRoles[contributorsroles scheme]
    end
    
    subgraph Output["📤 Output Generation"]
        FixtureGen[FixtureGenerator]
        FixtureGen --> |Generate sorted YAML| YAMLFixtures[YAML Fixtures<br/>ccmm_*.yaml]
        FixtureGen --> |Export sorted TTL| TurtleFile[vocabularies.ttl]
    end
    
    Loading --> Transformation
    Transformation --> Output
    
    style Input fill:#bbdefb
    style Loading fill:#c8e6c9
    style Transformation fill:#fff9c4
    style Output fill:#f8bbd0
```

## Module Dependencies

```mermaid
graph TD
    CLI[convert_vocabularies.py<br/>Main CLI Application]
    
    Store[rdf_store.py<br/>RDFTripleStore<br/>serialize_sorted]
    
    CSV[csv_loader.py<br/>CSVToRDFLoader]
    SPARQL[sparql_loader.py<br/>SPARQLLoader]
    YAML[yaml_loader.py<br/>YAMLToRDFLoader]
    SSSOM[sssom_loader.py<br/>SSSOMLoader]
    
    Transform[convert_vocabularies.py<br/>create_nma_vocabulary_terms<br/>_create_contributors_roles]
    
    Fixture[fixture_generator.py<br/>FixtureGenerator]
    Utils[utils.py<br/>print_statistics<br/>print_concept_schemes]
    
    CLI --> Store
    CLI --> CSV
    CLI --> SPARQL
    CLI --> YAML
    CLI --> SSSOM
    CLI --> Transform
    CLI --> Fixture
    CLI --> Utils
    
    CSV --> Store
    SPARQL --> Store
    YAML --> Store
    SSSOM --> Store
    Transform --> Store
    Fixture --> Store
    Utils --> Store
    
    style CLI fill:#4fc3f7
    style Store fill:#81c784
    style CSV fill:#ffb74d
    style SPARQL fill:#ffb74d
    style YAML fill:#ffb74d
    style SSSOM fill:#ffb74d
    style Transform fill:#fff59d
    style Fixture fill:#ba68c8
    style Utils fill:#ce93d8
```

## RDF Data Model

```mermaid
graph LR
    subgraph ExternalSources["External Vocabulary Sources"]
        CCMM[CCMM CSV<br/>vocabs.ccmm.cz]
        COAR[COAR RDF<br/>purl.org/coar]
        EU[EU Publications<br/>publications.europa.eu]
    end
    
    subgraph NMAScheme["NMA Vocabulary Scheme"]
        NMA[NMA Concepts<br/>nma.eosc.cz/vocabularies]
        NMA --> |skos:inScheme| NMAScheme[ConceptScheme]
        NMA --> |dc:identifier| ID[Identifier<br/>lowercase]
        NMA --> |skos:prefLabel| LabelCS[Label@cs]
        NMA --> |skos:prefLabel| LabelEN[Label@en]
        NMA --> |skos:definition| DefCS[Definition@cs]
        NMA --> |skos:definition| DefEN[Definition@en]
        NMA --> |skos:broader| Parent[Parent Concept<br/>within NMA scheme]
    end
    
    subgraph Relationships["Cross-Scheme Relationships"]
        NMA --> |skos:exactMatch| CCMM
        NMA --> |skos:exactMatch| COAR
        NMA --> |skos:exactMatch| EU
        NMA --> |skos:broadMatch| ExternalBroad[External Concepts]
    end
    
    subgraph SpecialCases["Special NMA Schemes"]
        Contributors[contributorsroles<br/>subset of AgentRole]
        Subjects[subjects<br/>for Invenio RDM]
    end
    
    style CCMM fill:#ffe0b2
    style COAR fill:#ffe0b2
    style EU fill:#ffe0b2
    style NMA fill:#a5d6a7
    style NMAScheme fill:#4fc3f7
    style Relationships fill:#fff59d
    style SpecialCases fill:#ce93d8
```

## Conversion Pipeline

```mermaid
sequenceDiagram
    participant User
    participant CLI as convert_vocabularies.py
    participant Store as RDFTripleStore
    participant Loaders as Various Loaders
    participant Transform as create_nma_vocabulary_terms
    participant Fixture as FixtureGenerator
    
    User->>CLI: Run with options<br/>(--input-dir, --sssom-dir, etc.)
    CLI->>Store: Initialize RDFTripleStore()
    Note over Store: Empty graph with<br/>default namespace bindings
    
    par Load CSV vocabularies
        CLI->>Loaders: CSVToRDFLoader.load_directory()
        Loaders->>Store: Add CCMM concepts<br/>with skos:broader hierarchy
    and Load SPARQL/RDF sources
        CLI->>Loaders: SPARQLLoader for<br/>EU Languages, File Types
        CLI->>Loaders: load_from_url for<br/>COAR Access Rights, Resource Types
        Loaders->>Store: Add external concepts
    and Load YAML vocabularies
        CLI->>Loaders: YAMLToRDFLoader for<br/>licenses.yaml, subject_schemes.yaml
        Loaders->>Store: Add NMA concepts directly
    and Load SSSOM mappings
        CLI->>Loaders: SSSOMLoader.load_directory()
        Loaders->>Store: Add mapping triples
    end
    
    Note over Store: Triplestore contains<br/>all source vocabularies
    
    CLI->>Transform: create_nma_vocabulary_terms()
    Transform->>Store: Query external schemes
    Transform->>Store: Create NMA concepts<br/>with skos:exactMatch
    Transform->>Store: _create_contributors_roles()<br/>Create contributorsroles subset
    
    CLI->>Fixture: FixtureGenerator.generate_all()
    Fixture->>Store: Query NMA schemes
    Fixture->>Fixture: Sort by hierarchy<br/>(parents before children)
    Fixture->>User: Write sorted YAML fixtures
    
    CLI->>Store: serialize_sorted(format="turtle")
    CLI->>User: Write vocabularies.ttl
    
    CLI->>Utils: print_statistics(), print_concept_schemes()
    Utils->>User: Display summary
    
    Note over User,Store: Pipeline complete<br/>All outputs are deterministic & sorted
```

## Key Design Decisions

### 1. Two-Phase Processing
- **Loading Phase**: All source data (CSV, RDF, YAML, SSSOM) is loaded into a single RDF triplestore
- **Transformation Phase**: External concepts are transformed to NMA scheme with proper mappings
- **Generation Phase**: Fixtures are generated from the unified triplestore

### 2. NMA Vocabulary Creation
The `create_nma_vocabulary_terms()` function:
- Queries each external scheme (COAR, EU Publications, CCMM)
- Creates corresponding NMA concepts with lowercase IDs
- Preserves all properties (labels, definitions, hierarchies)
- Adds `skos:exactMatch` to original external concepts
- Handles special cases like `contributorsroles` (subset of AgentRole)

### 3. Deterministic Output
- YAML fixtures: Sorted by ID, keys sorted alphabetically
- Turtle file: Uses `ttlser.DeterministicTurtleSerializer` for stable output
- Enables reliable Git diffs and reproducible builds

### 4. Hierarchy Preservation
- CSV loader creates `skos:broader` relationships using `parentId` column
- YAML loader converts parent IDs to lowercase for consistency
- Fixture generator respects hierarchy when sorting output

### 5. Namespace Handling
- External URIs preserved in `skos:exactMatch` relationships
- NMA IRIs use standardized format: `https://nma.eosc.cz/vocabularies/{type}/{id}`
- Lowercase IDs ensure consistency across all outputs
