"""
Polaris YAML to Coverity YAML Converter
Based on polaris_yaml_conversion.py from cop-migration-tools
"""

import copy
import re
import logging
import ruamel.yaml
from typing import Dict, Any, List

# Template for new Polaris coverity.yaml file
COVERITY_YAML_TEMPLATE = {
    'capture': {
        'build': {
            'clean-command': '',
            'build-command': '',
            'cov-build-args': []
        },
        'compiler-configuration': {
            'cov-configure': [],
        },
    },
    'analyze': {
        'cov-analyze-args': []
    }
}


def regulate_windows_commands(commands: List[str]) -> List[str]:
    """
    Commands with backslashes are adjusted for Windows compatibility
    """
    for idx, item in enumerate(commands):
        if item.find("\\") != -1 and item.find('"') == -1:
            item = item.replace("\\\\", "/").replace("\\", "/")
            new_item = '"' + item + '"'
            commands[idx] = new_item
    return commands


def parse_cop_yaml(cop_yaml: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse polaris.yml and extract relevant configuration
    """
    cop_config = {
        'project': {'name': '', 'branch': ''},
        'capture': {
            'build': {
                'clean-commands': '',
                'build-commands': '',
                'coverity': {
                    'cov-build': [],
                    'skip-files': [],
                    'cov-configure': []
                },
            },
            'file-system': []
        },
        'analyze': {
            'coverity': {
                'cov-analyze': []
            }
        },
    }

    # Extract project info
    if 'project' in cop_yaml:
        if 'name' in cop_yaml['project']:
            cop_config['project']['name'] = cop_yaml['project']['name'] or ""
        if 'branch' in cop_yaml['project']:
            cop_config['project']['branch'] = cop_yaml['project']['branch'] or ""
        else:
            del cop_config['project']['branch']

    # Extract capture configuration
    if 'capture' in cop_yaml:
        fatal_errors = []
        
        # Build and clean commands
        if 'build' in cop_yaml['capture']:
            if 'cleanCommands' in cop_yaml['capture']['build']:
                if len(cop_yaml['capture']['build']['cleanCommands']) > 1:
                    fatal_errors.append("coverity.yaml does not support multiple clean commands. Please combine them into one script.")
                else:
                    clean = cop_yaml['capture']['build']['cleanCommands'][0].get('shell', [])
                    new_clean = regulate_windows_commands(clean)
                    cop_config['capture']['build']['clean-commands'] = ' '.join(new_clean)
            
            if 'buildCommands' in cop_yaml['capture']['build']:
                if len(cop_yaml['capture']['build']['buildCommands']) > 1:
                    fatal_errors.append("coverity.yaml does not support multiple build commands. Please combine them into one script.")
                else:
                    build = cop_yaml['capture']['build']['buildCommands'][0].get('shell', [])
                    new_build = regulate_windows_commands(build)
                    cop_config['capture']['build']['build-commands'] = ' '.join(new_build)
            
            # Coverity-specific options
            if 'coverity' in cop_yaml['capture']['build']:
                if 'cov-build' in cop_yaml['capture']['build']['coverity']:
                    cov_build = cop_yaml['capture']['build']['coverity']['cov-build'] or []
                    cop_config['capture']['build']['coverity']['cov-build'] = list(cov_build)
                
                if 'cov-configure' in cop_yaml['capture']['build']['coverity']:
                    configure = []
                    opts = []
                    for opt in cop_yaml['capture']['build']['coverity']['cov-configure'] or []:
                        opts.append(opt)
                    configure.append(opts)
                    cop_config['capture']['build']['coverity']['cov-configure'] = configure
                
                if 'skipFiles' in cop_yaml['capture']['build']['coverity']:
                    skip_files = []
                    for opt in cop_yaml['capture']['build']['coverity']['skipFiles'] or []:
                        skip_files.append(opt)
                    cop_config['capture']['build']['coverity']['skip-files'] = skip_files
        
        # File system options
        if 'fileSystem' in cop_yaml['capture']:
            file_system = []
            if cop_yaml['capture']['fileSystem']:
                for item in cop_yaml['capture']['fileSystem']:
                    file_system.append("'" + item + "'" + ": " + str(cop_yaml['capture']['fileSystem'][item]))
                cop_config['capture']['file-system'] = file_system
        
        if fatal_errors:
            raise ValueError("\n".join(fatal_errors))

    # Extract analyze configuration
    if 'analyze' in cop_yaml:
        if 'coverity' in cop_yaml['analyze'] and 'cov-analyze' in cop_yaml['analyze']['coverity']:
            analyze = []
            for opt in cop_yaml['analyze']['coverity']['cov-analyze'] or []:
                analyze.append(opt)
            cop_config['analyze']['coverity']['cov-analyze'] = analyze

    return cop_config


def generate_coverity_yaml(cop_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate coverity.yaml configuration from parsed polaris.yml
    """
    coverity_yaml = copy.deepcopy(COVERITY_YAML_TEMPLATE)

    # Build commands
    if cop_config['capture']['build']['clean-commands']:
        coverity_yaml['capture']['build']['clean-command'] = cop_config['capture']['build']['clean-commands']
    else:
        del coverity_yaml['capture']['build']['clean-command']
    
    if cop_config['capture']['build']['build-commands']:
        coverity_yaml['capture']['build']['build-command'] = cop_config['capture']['build']['build-commands']
    else:
        del coverity_yaml['capture']['build']['build-command']
    
    if cop_config['capture']['build']['coverity']['cov-build']:
        coverity_yaml['capture']['build']['cov-build-args'] = cop_config['capture']['build']['coverity']['cov-build']
    else:
        del coverity_yaml['capture']['build']['cov-build-args']
    
    # Compiler configuration
    if cop_config['capture']['build']['coverity']['cov-configure']:
        covconfs = cop_config['capture']['build']['coverity']['cov-configure'][-1]
        for conf in covconfs:
            coverity_yaml['capture']['compiler-configuration']['cov-configure'].append(conf)
    
    # Analyze args
    coverity_yaml['analyze']['cov-analyze-args'] = cop_config['analyze']['coverity']['cov-analyze']

    # Remove empty build section
    if not coverity_yaml['capture']['build']:
        del coverity_yaml['capture']['build']

    # Handle skip files
    if cop_config['capture']['build']['coverity']['skip-files']:
        skipconfig = {}
        langs = ["java", "gcc", "msvc", "cs", "go", "vb", "clang", "dart", "kotlin"]
        
        for skip in cop_config['capture']['build']['coverity']['skip-files']:
            match = re.search(r"@(.*):(.*)", skip)
            cskips = ["c", "c++", "objc", "objc++"]
            
            if match:
                if match.group(1) == "java":
                    skipconfig.setdefault('java', []).append(match.group(2))
                elif match.group(1) in cskips:
                    skipconfig.setdefault('gcc', []).append(match.group(2))
                    skipconfig.setdefault('msvc', []).append(match.group(2))
                    skipconfig.setdefault('clang', []).append(match.group(2))
                else:
                    logging.warning(f"Unhandled skip language: {match.group(1)}")
                continue
            
            for lang in langs:
                skipconfig.setdefault(f"{lang}", []).append(skip)
        
        for lang in skipconfig:
            config = [f"--{lang}"]
            for skip in skipconfig[lang]:
                config.append(f"--xml-option=skip_file:{skip}")
            coverity_yaml['capture']['compiler-configuration']['cov-configure'].append(config)
    elif cop_config['capture']['build']['coverity']['cov-configure'] == []:
        del coverity_yaml['capture']['compiler-configuration']

    # Handle file system exclusions
    if cop_config['capture']['file-system']:
        for file in cop_config['capture']['file-system']:
            if file is not None:
                match = re.search(r"'excludeRegex'\s*:\s*'(.*)'", file)
                if match:
                    if "files" not in coverity_yaml['capture']:
                        coverity_yaml['capture']['files'] = {}
                    if "exclude-regex" in coverity_yaml['capture']['files']:
                        coverity_yaml['capture']['files']['exclude-regex'] += "|(" + match.group(1) + ")"
                    else:
                        coverity_yaml['capture']['files']['exclude-regex'] = "(" + match.group(1) + ")"

    return coverity_yaml


def convert_polaris_to_coverity(polaris_yaml_content: str) -> tuple[str, Dict[str, Any], str]:
    """
    Main conversion function
    Returns: (coverity_yaml_string, metadata_dict, original_polaris_content)
    """
    try:
        yaml = ruamel.yaml.YAML()
        yaml.width = 1000
        
        # Parse polaris.yml
        cop_yaml = yaml.load(polaris_yaml_content)
        
        # Extract configuration
        cop_config = parse_cop_yaml(cop_yaml)
        
        # Generate coverity.yaml
        coverity_yaml = generate_coverity_yaml(cop_config)
        
        # Convert to string
        from io import StringIO
        stream = StringIO()
        yaml.dump(coverity_yaml, stream)
        coverity_yaml_str = stream.getvalue()
        
        # Prepare metadata
        metadata = {
            'project_name': cop_config['project']['name'],
            'branch': cop_config['project'].get('branch', 'N/A'),
            'has_build_command': bool(cop_config['capture']['build']['build-commands']),
            'has_clean_command': bool(cop_config['capture']['build']['clean-commands']),
            'has_cov_build_args': bool(cop_config['capture']['build']['coverity']['cov-build']),
            'has_cov_analyze_args': bool(cop_config['analyze']['coverity']['cov-analyze']),
        }
        
        return coverity_yaml_str, metadata, polaris_yaml_content
        
    except Exception as e:
        raise Exception(f"Conversion failed: {str(e)}")
