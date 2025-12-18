# 📊 Legacy Config Cleanup Dashboard

## Overview
The Dashboard provides real-time statistics and metrics for legacy configuration scanning results. It is integrated directly into the Legacy Config Cleanup page and displays after a scan completes.

## Features Implemented

### **Summary Metrics Cards** 📦
The dashboard displays 5 key metric cards showing scan results:

1. **📄 Legacy Files Found**
   - Total count of legacy configuration files detected
   - Blue gradient background

2. **📦 Affected Repositories**
   - Number of unique repositories containing legacy configs
   - Purple gradient background

3. **🌿 Branches Scanned**
   - Count of distinct branches that were scanned
   - Pink gradient background

4. **🔑 Keywords Matched**
   - Number of unique legacy keywords detected (coverity, polaris, blackduck, etc.)
   - Purple gradient background

5. **⏱️ Scan Duration**
   - Shows the total time taken to complete the scan
   - Displays in MM:SS format
   - Green gradient background
   - Only appears when scan duration > 0
   - Uses `useRef` for accurate timing

## Technical Details

### Frontend Components
- **Dashboard.js**: Main dashboard component (~115 lines)
- **Location**: Embedded in `LegacyConfigCleanup.js` component
- **Props**:
  - `legacyFiles`: Array of scanned legacy configuration files
  - `scanDuration`: Total scan time in seconds (from `completedScanDuration` state)
- **Recharts Library**: Used for responsive metric cards
- **No Backend API**: All metrics calculated client-side from `legacyFiles` prop

### Data Flow
```javascript
// Dashboard receives two props
<Dashboard 
  legacyFiles={legacyFiles}           // Array of found files
  scanDuration={completedScanDuration} // Scan time in seconds
/>
```

### Metric Calculations
```javascript
// All metrics computed from legacyFiles array
const totalFiles = legacyFiles.length;
const repositories = [...new Set(legacyFiles.map(f => f.repository))];
const branches = [...new Set(legacyFiles.map(f => f.branch || 'main'))];
const keywordStats = {}; // Count of each keyword matched
```

### Scan Timing Implementation
- **Uses `useRef`** for accurate timing (not state-based)
- **Start**: `scanStartTimeRef.current = Date.now()`
- **Live Timer**: Updates every second during scan using `setInterval`
- **Completion**: Calculates `Math.floor((Date.now() - scanStartTimeRef.current) / 1000)`
- **Display**: MM:SS format with zero-padding

### Styling
- Modern gradient backgrounds for each metric card
- Fully responsive grid layout
- Smooth transitions and hover effects
- Empty state when no scan data available
- Consistent with application theme

## Usage

### Accessing the Dashboard
1. Navigate to the **🧹 Legacy Config Cleanup** tab
2. Click the **"Scan for Legacy Configs"** button
3. During scan: Live timer displays scan progress
4. After scan: Dashboard appears automatically with results

### Dashboard States

#### Empty State
When no scan has been performed:
- Shows empty icon (📊)
- Message: "No Scan Data Available"
- Prompt to run a scan

#### Active Scan
While scanning is in progress:
- Live timer counts up showing elapsed time
- Blue gradient background
- Format: "Scan Duration: MM:SS"

#### Results Display
After scan completes:
- 5 metric cards appear with scan statistics
- Scan duration card shows final time
- Below dashboard: Paginated table with detailed file list

## Pagination Features

Integrated with the dashboard results:
- **Page Sizes**: 10, 20, 50, or 100 items per page
- **Navigation**: First, Previous, Next, Last buttons
- **Page Info**: Shows "Page X of Y (Z total files)"
- **Auto-reset**: Returns to page 1 when filters change
- **Filter Support**: Works with repository, reason, keyword, and branch filters

## Integration with Legacy Cleanup

### Component Hierarchy
```
LegacyConfigCleanup
├── Scan Controls (button + timer)
├── Dashboard (metrics cards) ← conditionally rendered
└── Results Table (paginated)
```

### Data Flow
```
Scan Button Click → 
  scanStartTimeRef.current = Date.now() →
  GitHub API calls →
  legacyFiles state updated →
  completedScanDuration calculated →
  Dashboard renders with props
```

## Performance Considerations
- **Client-side calculations**: No API calls, instant metric updates
- **Conditional rendering**: Dashboard only renders when legacyFiles.length > 0
- **Efficient filtering**: Uses Set for unique value calculations
- **Ref-based timing**: Accurate scan duration without re-render overhead

## Troubleshooting

### Dashboard Not Appearing
- **Cause**: No scan has been performed yet
- **Solution**: Click "Scan for Legacy Configs" button to run a scan

### Scan Duration Shows 0:00
- **Cause**: `scanStartTimeRef.current` was null during scan
- **Solution**: Verify console logs show "Scan started at: [timestamp]"
- **Technical**: Uses `useRef` instead of state for synchronous timing

### Live Timer Not Updating
- **Cause**: `useEffect` interval not running
- **Solution**: Check that `scanning` state is true and `scanStartTimeRef.current` is set
- **Technical**: Timer updates every 1 second via `setInterval`

### Scan Duration Card Missing
- **Cause**: `scanDuration` is null or 0
- **Solution**: Ensure scan completes successfully
- **Technical**: Card only renders when `scanDuration !== null && scanDuration > 0`

## Console Logging

For debugging, the following logs are available:
```javascript
// When scan starts
"Scan started at: [timestamp]"

// When scan completes
"Scan completion - now: [timestamp] scanStartTime: [timestamp] duration: [seconds]"

// When Dashboard renders
"Dashboard received scanDuration: [value]"
```

---

**Next Steps**: Navigate to Legacy Config Cleanup and run your first scan to see the dashboard in action!
