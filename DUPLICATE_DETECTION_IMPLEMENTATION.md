# Workflow Duplicate Detection & Removal Implementation

## Overview

This document describes the implementation of duplicate detection and removal functionality for GitHub Actions workflow files. The system can detect exact matches between workflow files and templates at three levels: complete workflows, individual jobs, and step sequences.

## Features

### 1. Duplicate Detection Levels

#### Complete Workflow Duplicates
- Detects when an entire workflow file matches a template
- Recommends removing the entire workflow file
- Useful for cleaning up redundant workflow files

#### Job-Level Duplicates
- Detects when individual jobs in a workflow match template jobs
- Recommends removing specific jobs from workflows
- Preserves other jobs in the workflow

#### Step-Level Duplicates
- Detects when consecutive step sequences match template steps
- Recommends removing specific step ranges from jobs
- Preserves other steps in the job

### 2. Removal Options

#### Pull Request Method
- Creates a new branch with the changes
- Generates a pull request for review
- Allows team collaboration before merging
- **Recommended for production repositories**

#### Direct Commit Method
- Applies changes directly to the specified branch
- Faster for personal repositories or testing
- **Use with caution in shared repositories**

## Backend Implementation

### Core Components

#### 1. DuplicateDetector Class
**File:** [`backend/workflow_duplicate_detector.py`](backend/workflow_duplicate_detector.py:11-350)

**Key Methods:**
- [`normalize_yaml_content()`](backend/workflow_duplicate_detector.py:17-27) - Normalizes YAML for comparison
- [`compare_yaml_structures()`](backend/workflow_duplicate_detector.py:29-54) - Deep semantic comparison
- [`detect_workflow_duplicate()`](backend/workflow_duplicate_detector.py:158-191) - Complete workflow matching
- [`detect_job_duplicates()`](backend/workflow_duplicate_detector.py:56-99) - Job-level matching
- [`detect_step_duplicates()`](backend/workflow_duplicate_detector.py:101-156) - Step sequence matching
- [`detect_all_duplicates()`](backend/workflow_duplicate_detector.py:193-265) - Comprehensive detection
- [`remove_job_from_workflow()`](backend/workflow_duplicate_detector.py:267-303) - Job removal
- [`remove_steps_from_job()`](backend/workflow_duplicate_detector.py:305-350) - Step removal

#### 2. API Endpoints

##### Detect Duplicates Endpoint
**Endpoint:** `POST /api/workflows/detect-duplicates`
**File:** [`backend/main.py`](backend/main.py:2279-2418)

**Request:**
```json
{
  "repository": "owner/repo",
  "workflow_file_path": ".github/workflows/ci.yml",
  "template_ids": [1, 2, 3]  // Optional, checks all templates if omitted
}
```

**Response:**
```json
{
  "success": true,
  "repository": "owner/repo",
  "workflow_file": ".github/workflows/ci.yml",
  "duplicates_found": true,
  "duplicates": {
    "workflow_duplicates": [
      {
        "template_id": 1,
        "template_name": "Black Duck SCA Workflow",
        "match_percentage": 100,
        "can_remove_file": true,
        "reasoning": "Entire workflow matches template 'Black Duck SCA Workflow'"
      }
    ],
    "job_duplicates": [
      {
        "template_id": 2,
        "template_name": "Polaris SAST Job",
        "job_name": "security-scan",
        "match_percentage": 100,
        "can_remove": true,
        "reasoning": "Job 'security-scan' matches template 'Polaris SAST Job'"
      }
    ],
    "step_duplicates": [
      {
        "template_id": 3,
        "template_name": "Coverity Steps",
        "job_name": "build",
        "step_indices": [3, 4, 5],
        "step_count": 3,
        "match_percentage": 100,
        "can_remove": true,
        "reasoning": "3 steps in job 'build' match template 'Coverity Steps'"
      }
    ]
  },
  "summary": {
    "complete_workflow_matches": 1,
    "duplicate_jobs": 1,
    "duplicate_step_sequences": 1,
    "total_templates_checked": 10
  }
}
```

##### Remove Duplicates Endpoint
**Endpoint:** `POST /api/workflows/remove-duplicates`
**File:** [`backend/main.py`](backend/main.py:2421-2667)

**Request:**
```json
{
  "repository": "owner/repo",
  "workflow_file_path": ".github/workflows/ci.yml",
  "duplicates_to_remove": [
    {
      "type": "job",
      "job_name": "security-scan"
    },
    {
      "type": "steps",
      "job_name": "build",
      "step_indices": [3, 4, 5]
    }
  ],
  "method": "pull_request",  // or "direct"
  "branch_name": "remove-duplicates-20250114",  // Optional
  "commit_message": "Remove duplicate workflow content"  // Optional
}
```

**Response (Pull Request):**
```json
{
  "success": true,
  "action": "content_modified",
  "workflow_file": ".github/workflows/ci.yml",
  "branch": "remove-duplicates-20250114",
  "method": "pull_request",
  "pr_url": "https://github.com/owner/repo/pull/123",
  "jobs_removed": 1,
  "step_sequences_removed": 1,
  "message": "Duplicate content removed from .github/workflows/ci.yml"
}
```

**Response (File Removal):**
```json
{
  "success": true,
  "action": "file_removed",
  "workflow_file": ".github/workflows/duplicate.yml",
  "branch": "main",
  "method": "direct",
  "pr_url": null,
  "message": "Workflow file .github/workflows/duplicate.yml removed successfully"
}
```

#### 3. AI Analysis Integration

The duplicate detection is now integrated into the AI analysis workflow:

**File:** [`backend/main.py`](backend/main.py:1528-1809)

**Changes:**
1. Added `DuplicateDetector` initialization
2. Fetches all templates for comparison
3. Detects duplicates for each workflow file during analysis
4. Includes duplicate results in the analysis response

**Response Structure:**
```json
{
  "repositories": [
    {
      "repository": "owner/repo",
      "blackduck_analysis": {
        "status": "configured",
        "workflow_duplicates": [
          {
            "workflow_file": "ci.yml",
            "workflow_path": ".github/workflows/ci.yml",
            "duplicates": {
              "has_duplicates": true,
              "complete_workflow_duplicate": null,
              "job_duplicates": [...],
              "step_duplicates": [...]
            }
          }
        ]
      }
    }
  ]
}
```

## Frontend Implementation (To Be Completed)

### Required UI Components

#### 1. Duplicate Detection Display
- Show duplicate detection results in analysis modal
- Display different icons/badges for each duplicate type:
  - 🗑️ Complete workflow duplicate
  - 📦 Job duplicate
  - 🔧 Step sequence duplicate

#### 2. Removal Action Buttons
For each detected duplicate:
- **"Remove via PR"** button - Creates pull request
- **"Remove Directly"** button - Direct commit (with confirmation)
- **"View Details"** button - Shows exact matching content

#### 3. Confirmation Dialogs
- Confirm before removing duplicates
- Show preview of what will be removed
- Option to select removal method (PR vs Direct)

#### 4. Status Notifications
- Success: "Pull request created for duplicate removal"
- Success: "Duplicates removed successfully"
- Error: "Failed to remove duplicates: [reason]"

### Recommended UI Flow

```
1. User runs AI Analysis
   ↓
2. Results show repositories with duplicates
   ↓
3. User clicks "View Duplicates" for a repository
   ↓
4. Modal shows:
   - Workflow file name
   - Duplicate type (workflow/job/steps)
   - Template name that matches
   - Match percentage
   - Removal options
   ↓
5. User selects duplicates to remove
   ↓
6. User chooses removal method:
   - Pull Request (recommended)
   - Direct Commit
   ↓
7. Confirmation dialog
   ↓
8. API call to remove duplicates
   ↓
9. Success notification with link to PR/commit
```

## Usage Examples

### Example 1: Detect and Remove Complete Workflow Duplicate

```javascript
// 1. Detect duplicates
const detectResponse = await fetch('http://localhost:8000/api/workflows/detect-duplicates', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    repository: 'myorg/myrepo',
    workflow_file_path: '.github/workflows/blackduck.yml'
  })
});

const detection = await detectResponse.json();

// 2. If complete workflow duplicate found, remove the file
if (detection.duplicates.workflow_duplicates.length > 0) {
  const removeResponse = await fetch('http://localhost:8000/api/workflows/remove-duplicates', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      repository: 'myorg/myrepo',
      workflow_file_path: '.github/workflows/blackduck.yml',
      duplicates_to_remove: [
        {
          type: 'complete_workflow',
          can_remove_file: true
        }
      ],
      method: 'pull_request',
      commit_message: 'Remove duplicate Black Duck workflow'
    })
  });
  
  const result = await removeResponse.json();
  console.log('PR created:', result.pr_url);
}
```

### Example 2: Remove Specific Jobs and Steps

```javascript
const removeResponse = await fetch('http://localhost:8000/api/workflows/remove-duplicates', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    repository: 'myorg/myrepo',
    workflow_file_path: '.github/workflows/ci.yml',
    duplicates_to_remove: [
      {
        type: 'job',
        job_name: 'duplicate-security-scan'
      },
      {
        type: 'steps',
        job_name: 'build',
        step_indices: [5, 6, 7]
      }
    ],
    method: 'pull_request',
    branch_name: 'cleanup-duplicates',
    commit_message: 'Remove duplicate security scanning steps'
  })
});
```

## Technical Details

### Semantic YAML Comparison

The duplicate detector uses semantic comparison rather than string comparison:

1. **Normalization:** Both workflow and template YAML are parsed and normalized
2. **Structure Comparison:** Deep comparison of YAML structures (dicts, lists, values)
3. **Whitespace Agnostic:** Formatting differences don't affect matching
4. **Order Sensitive:** Step order matters for step sequence matching

### Match Percentage Calculation

Currently, the system uses exact matching (100% or 0%). Future enhancements could include:
- Partial matching with configurable threshold
- Similarity scoring for near-duplicates
- Fuzzy matching for minor variations

### Safety Features

1. **Preview Before Removal:** Detection endpoint shows what would be removed
2. **Pull Request Option:** Changes can be reviewed before merging
3. **Atomic Operations:** Each removal is a single commit
4. **Error Handling:** Comprehensive error messages for troubleshooting

## Testing

### Manual Testing Steps

1. **Test Complete Workflow Duplicate:**
   ```bash
   # Create a workflow that exactly matches a template
   # Run detection
   # Verify it's detected as complete duplicate
   # Remove via PR
   # Verify PR is created correctly
   ```

2. **Test Job Duplicate:**
   ```bash
   # Create a workflow with a job matching a template job
   # Run detection
   # Verify job is detected as duplicate
   # Remove the job
   # Verify other jobs remain intact
   ```

3. **Test Step Duplicate:**
   ```bash
   # Create a workflow with steps matching a template
   # Run detection
   # Verify steps are detected as duplicate
   # Remove the steps
   # Verify other steps remain intact
   ```

### Automated Testing

Create test cases in `backend/test_duplicate_detection.py`:

```python
def test_detect_complete_workflow_duplicate():
    # Test complete workflow matching
    pass

def test_detect_job_duplicate():
    # Test job-level matching
    pass

def test_detect_step_duplicate():
    # Test step sequence matching
    pass

def test_remove_job_from_workflow():
    # Test job removal
    pass

def test_remove_steps_from_job():
    # Test step removal
    pass

def test_remove_entire_workflow_file():
    # Test file deletion
    pass
```

## Future Enhancements

1. **Partial Matching:** Detect near-duplicates with similarity threshold
2. **Batch Operations:** Remove duplicates from multiple workflows at once
3. **Dry Run Mode:** Preview all changes before applying
4. **Rollback Support:** Undo duplicate removals
5. **Duplicate Prevention:** Warn when adding content that duplicates templates
6. **Analytics:** Track duplicate patterns across repositories
7. **Smart Merging:** Suggest consolidating similar workflows

## Security Considerations

1. **GitHub Token:** Requires valid GITHUB_TOKEN with appropriate permissions
2. **Repository Access:** User must have write access to create PRs/commits
3. **Branch Protection:** Respects branch protection rules
4. **Audit Trail:** All changes are tracked via Git commits
5. **Review Process:** Pull request method enables code review

## Troubleshooting

### Common Issues

**Issue:** Duplicate not detected
- **Cause:** Formatting differences, comments, or variable names
- **Solution:** Check YAML structure, ensure exact semantic match

**Issue:** Removal fails
- **Cause:** Insufficient permissions, branch protection
- **Solution:** Verify GitHub token scopes, check repository settings

**Issue:** PR creation fails
- **Cause:** Branch already exists, conflicts
- **Solution:** Use unique branch names, resolve conflicts manually

## Summary

The duplicate detection and removal system provides:
- ✅ Three-level duplicate detection (workflow, job, step)
- ✅ Safe removal via pull requests or direct commits
- ✅ Integration with AI analysis workflow
- ✅ Comprehensive API endpoints
- ⏳ Frontend UI (in progress)
- ⏳ Automated testing (to be implemented)

This feature helps maintain clean, efficient GitHub Actions workflows by identifying and removing redundant content that matches existing templates.