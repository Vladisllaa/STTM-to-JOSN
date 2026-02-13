# Scripts Directory

This directory contains utility scripts for generating SQL and contract files.

## Available Scripts

### 1. Generate SQL Files
```bash
python gdat_sql/generate_sql.py
```
- Generates SQL files from templates
- Configure settings in `gdat_sql/generate_sql.py`

### 2. Generate Contract Files
```bash
python gdat_contracts/generate_contracts.py
```
- Processes ZIP files from `workdir/`
- Generates contract JSON files
- Configure settings in `gdat_contracts/generate_contracts.py`

## Usage
1. Place ZIP files in the `workdir/` directory
2. Run the desired script
3. Check output in respective output directories

## Configuration
- Edit Python files to adjust:
  - Database connections
  - File paths
  - Naming conventions
  - Other generation parameters

## Example
See `STTM/` for example ZIP files and expected output format.