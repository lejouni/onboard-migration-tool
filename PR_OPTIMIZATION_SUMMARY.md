# PR Event Optimization for Polaris Scans

## 🎯 Feature Overview

Automatically optimize Polaris SAST scan performance by using **SAST_RAPID** mode for pull request events while maintaining full SAST depth for main branch commits.

## ⚡ How It Works

### Smart Event Detection
```yaml
polaris_test_sast_type: ${{ github.event_name == 'pull_request' && 'SAST_RAPID' || '' }}
```

This single line:
- Detects if the workflow is triggered by a pull request event
- Sets `polaris_test_sast_type: 'SAST_RAPID'` for PRs (faster scans)
- Leaves it empty for push/schedule events (full SAST)

## 📊 Performance Impact

| Event Type | SAST Mode | Speed | Purpose |
|------------|-----------|-------|---------|
| **Pull Request** | SAST_RAPID | ⚡ **30-70% faster** | Quick developer feedback |
| **Push to main** | Full SAST | 🔍 Thorough | Comprehensive analysis |
| **Scheduled** | Full SAST | 🔍 Thorough | Deep security audit |
| **Manual** | Full SAST | 🔍 Thorough | On-demand analysis |

## 🎨 Complete Example

### Java Project with Maven

**Before** (no optimization):
```yaml
- name: Polaris SAST Scan
  uses: blackduck-inc/black-duck-security-scan@v2
  with:
    polaris_server_url: ${{ vars.POLARIS_SERVER_URL }}
    polaris_access_token: ${{ secrets.POLARIS_ACCESS_TOKEN }}
    polaris_assessment_types: 'SAST,SCA'
    polaris_prComment_enabled: true
    github_token: ${{ secrets.GITHUB_TOKEN }}
```

**After** (with PR optimization):
```yaml
- name: Polaris SAST Scan
  uses: blackduck-inc/black-duck-security-scan@v2
  with:
    polaris_server_url: ${{ vars.POLARIS_SERVER_URL }}
    polaris_access_token: ${{ secrets.POLARIS_ACCESS_TOKEN }}
    polaris_assessment_types: 'SAST,SCA'
    
    # PR Optimization: Fast scans for pull requests
    polaris_test_sast_type: ${{ github.event_name == 'pull_request' && 'SAST_RAPID' || '' }}
    
    polaris_prComment_enabled: true
    github_token: ${{ secrets.GITHUB_TOKEN }}
```

## ✅ Benefits

### For Developers
- **Faster PR feedback**: Get security results 30-70% quicker
- **Reduced wait times**: Less time in CI/CD queue
- **Same quality**: Still catches critical issues

### For Teams
- **Optimized resources**: Lower compute costs for PR builds
- **Better velocity**: Faster merge cycles
- **Compliance maintained**: Full scans on main branch

### For Security
- **No compromise**: Full SAST on production branches
- **Early detection**: Critical issues still caught in PRs
- **Best practice**: Industry-standard optimization

## 🔍 When It Applies

The optimization is **automatically included** when:

1. ✅ Repository has (or will have) pull request triggers
2. ✅ Polaris SAST is being configured
3. ✅ Assessment types include 'SAST' (SAST-only or SAST,SCA)

**NOT applied** when:
- ❌ Assessment type is SCA-only (no SAST component)
- ❌ User explicitly removes it from template

## 🧪 Testing Scenarios

### Scenario 1: Pull Request Event
```bash
# Trigger: Pull request opened/updated
Event: pull_request
Result: polaris_test_sast_type = 'SAST_RAPID'
Scan: Fast SAST + Full SCA
Time: ~5-10 minutes (Java project)
```

### Scenario 2: Push to Main
```bash
# Trigger: Merged to main branch
Event: push
Result: polaris_test_sast_type = '' (empty)
Scan: Full SAST + Full SCA
Time: ~15-30 minutes (Java project)
```

### Scenario 3: Manual Workflow
```bash
# Trigger: workflow_dispatch (manual)
Event: workflow_dispatch
Result: polaris_test_sast_type = '' (empty)
Scan: Full SAST + Full SCA
Time: ~15-30 minutes (Java project)
```

## 📝 Implementation in AI-Analysis

### Detection Logic
```python
def should_add_pr_optimization(assessment_types, workflow_triggers):
    """
    Determine if PR optimization should be added
    """
    # Only for SAST assessments
    if 'SAST' not in assessment_types:
        return False
    
    # Check if workflow has PR triggers
    has_pr_trigger = 'pull_request' in workflow_triggers
    
    # Recommend even if no PR trigger yet (good practice)
    return True
```

### Template Generation
```python
def generate_polaris_step(language, assessment_types, package_manager):
    """
    Generate Polaris step with PR optimization
    """
    config = {
        'polaris_assessment_types': assessment_types,
    }
    
    # Add PR optimization for SAST
    if 'SAST' in assessment_types:
        config['polaris_test_sast_type'] = (
            "${{ github.event_name == 'pull_request' && 'SAST_RAPID' || '' }}"
        )
    
    return render_template('polaris-step.yml', config)
```

## 🎯 User Experience

### Recommendation Card
```
┌─────────────────────────────────────────────────────┐
│ 🔧 Enhance Existing Workflow                       │
├─────────────────────────────────────────────────────┤
│ File: `.github/workflows/maven-ci.yml`             │
│                                                     │
│ 📊 Recommended Addition:                           │
│ Add "Polaris Security Scan" job                    │
│                                                     │
│ ✓ SAST + SCA analysis (pom.xml detected)          │
│ ✓ Optimized for PR performance                     │
│   - Pull requests: Fast SAST_RAPID scans          │
│   - Main branch: Comprehensive full SAST           │
│ ✓ PR comments enabled                             │
│                                                     │
│ [View Diff] [Apply Changes]                        │
└─────────────────────────────────────────────────────┘
```

### Diff Preview
When user clicks "View Diff", they see:
```diff
+ polaris-security-scan:
+   runs-on: ubuntu-latest
+   name: Polaris Security Analysis
+   steps:
+     - uses: actions/checkout@v4
+     - name: Polaris SAST+SCA Scan
+       uses: blackduck-inc/black-duck-security-scan@v2
+       with:
+         polaris_assessment_types: 'SAST,SCA'
+         # Fast scans for PRs, full scans for main
+         polaris_test_sast_type: ${{ github.event_name == 'pull_request' && 'SAST_RAPID' || '' }}
```

## 📚 Technical Details

### GitHub Event Name Values
```yaml
pull_request          # PR opened, synchronized, reopened
pull_request_target   # PR from fork (use cautiously)
push                  # Commit pushed to branch
workflow_dispatch     # Manual trigger
schedule              # Cron/scheduled run
```

### Expression Evaluation
```yaml
# Expression
${{ github.event_name == 'pull_request' && 'SAST_RAPID' || '' }}

# When event_name = 'pull_request'
→ true && 'SAST_RAPID' || ''
→ 'SAST_RAPID'

# When event_name = 'push'
→ false && 'SAST_RAPID' || ''
→ false || ''
→ ''
```

### Empty String Behavior
When `polaris_test_sast_type: ''` (empty):
- Black Duck action ignores the parameter
- Defaults to full SAST analysis
- Same as not setting the parameter at all

## 🔒 Security Considerations

### Coverage Level
- **SAST_RAPID**: Focuses on high/critical issues, incremental changes
- **Full SAST**: Complete dataflow analysis, all severity levels

### When to Use Full SAST
✅ Production branch commits (main, master, release)
✅ Scheduled security audits
✅ Compliance/regulatory scans
✅ Release candidates

### When SAST_RAPID Is Sufficient
✅ Pull request reviews
✅ Feature branch development
✅ Quick feedback iterations
✅ Developer workflow optimization

## 🚀 Rollout Strategy

### Phase 1: New Recommendations
- All new Polaris recommendations include PR optimization
- Clearly communicate the feature in UI

### Phase 2: Existing Workflows
- Offer to enhance existing Polaris workflows
- Show diff highlighting the optimization addition

### Phase 3: Analytics
- Track scan time improvements
- Measure developer satisfaction
- Adjust based on feedback

## 📈 Success Metrics

Track these metrics to measure success:

1. **Performance**: PR scan time reduction (target: 30-70%)
2. **Adoption**: % of workflows using optimization (target: 90%+)
3. **Coverage**: Issues caught in SAST_RAPID vs Full (target: 95%+ of critical)
4. **Velocity**: Time to merge reduction (target: 10-20%)

## ❓ FAQ

**Q: Will SAST_RAPID miss security issues?**
A: SAST_RAPID focuses on high/critical issues and incremental changes. Full SAST still runs on main branch, ensuring comprehensive coverage.

**Q: Can I override this for specific PRs?**
A: Yes, manually trigger the workflow with `workflow_dispatch` for full SAST, or temporarily modify the workflow.

**Q: Does this affect SCA scans?**
A: No, SCA always runs at full depth. Only SAST is optimized.

**Q: What if I don't want PR optimization?**
A: You can edit the template before applying and remove the `polaris_test_sast_type` line.

**Q: Is this a Black Duck best practice?**
A: Yes, this is a recommended optimization for balancing speed and security in CI/CD pipelines.

## 🔗 Related Documentation

- [Black Duck Security Scan Action](https://github.com/blackduck-inc/black-duck-security-scan)
- [Polaris Documentation](https://sig-product-docs.synopsys.com/bundle/polaris/page/polaris.html)
- [GitHub Actions Events](https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows)
- [WORKFLOW_ENHANCEMENT_PLAN.md](./WORKFLOW_ENHANCEMENT_PLAN.md) - Full feature specification

---

**Last Updated**: November 12, 2025
**Feature Status**: Planned (included in workflow enhancement plan)
