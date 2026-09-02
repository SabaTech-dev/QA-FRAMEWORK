import { useState, useEffect, useCallback } from 'react'
import {
  Box,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Chip,
  IconButton,
  Collapse,
  Button,
  Typography,
} from '@mui/material'
import {
  FilterList,
  Close,
  Save,
  Search,
} from '@mui/icons-material'

export interface FilterConfig {
  search?: string
  status?: string
  environment?: string
  testType?: string
  dateFrom?: string
  dateTo?: string
  tags?: string[]
}

interface AdvancedFilterProps {
  onFilterChange: (filters: FilterConfig) => void
  savedFilters?: { name: string; config: FilterConfig }[]
  onSaveFilter?: (name: string, config: FilterConfig) => void
}

export default function AdvancedFilter({
  onFilterChange,
  savedFilters = [],
  onSaveFilter,
}: AdvancedFilterProps) {
  const [expanded, setExpanded] = useState(false)
  const [filters, setFilters] = useState<FilterConfig>({})
  const [tagInput, setTagInput] = useState('')
  const [presetName, setPresetName] = useState('')

  // Debounced search
  useEffect(() => {
    const timer = setTimeout(() => {
      onFilterChange(filters)
    }, 300)
    return () => clearTimeout(timer)
  }, [filters, onFilterChange])

  const handleFilterChange = useCallback((key: keyof FilterConfig, value: any) => {
    setFilters(prev => ({ ...prev, [key]: value }))
  }, [])

  const handleAddTag = () => {
    if (tagInput.trim() && !filters.tags?.includes(tagInput.trim())) {
      setFilters(prev => ({
        ...prev,
        tags: [...(prev.tags || []), tagInput.trim()],
      }))
      setTagInput('')
    }
  }

  const handleRemoveTag = (tag: string) => {
    setFilters(prev => ({
      ...prev,
      tags: prev.tags?.filter(t => t !== tag),
    }))
  }

  const handleSavePreset = () => {
    if (presetName.trim() && onSaveFilter) {
      onSaveFilter(presetName.trim(), filters)
      setPresetName('')
    }
  }

  const handleLoadPreset = (config: FilterConfig) => {
    setFilters(config)
  }

  const handleClearFilters = () => {
    setFilters({})
  }

  const activeFilterCount = Object.values(filters).filter(v => 
    v !== undefined && v !== '' && (Array.isArray(v) ? v.length > 0 : true)
  ).length

  return (
    <Box sx={{ mb: 2 }}>
      <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}  >
        <IconButton onClick={() => setExpanded(!expanded)}>
          <FilterList />
        </IconButton>
        <TextField
          size="small"
          placeholder="Search..."
          value={filters.search || ''}
          onChange={(e) => handleFilterChange('search', e.target.value)}
          slotProps={{ input: {
            startAdornment: <Search sx={{ mr: 1, color: 'text.secondary' }} />,
          } }}
          sx={{ flexGrow: 1, maxWidth: 400 }}
        />
        {activeFilterCount > 0 && (
          <Chip
            label={`${activeFilterCount} filter${activeFilterCount > 1 ? 's' : ''} active`}
            color="primary"
            size="small"
            onDelete={handleClearFilters}
          />
        )}
      </Box>

      <Collapse in={expanded}>
        <Box sx={{ mt: 2, p: 2, bgcolor: 'background.paper', borderRadius: 1 }}>
          <Grid container spacing={2}>
            <Grid size={{ xs: 12, sm: 6, md: 3 }}   >
              <FormControl fullWidth size="small">
                <InputLabel>Status</InputLabel>
                <Select
                  value={filters.status || ''}
                  label="Status"
                  onChange={(e) => handleFilterChange('status', e.target.value)}
                >
                  <MenuItem value="">All</MenuItem>
                  <MenuItem value="completed">Completed</MenuItem>
                  <MenuItem value="running">Running</MenuItem>
                  <MenuItem value="failed">Failed</MenuItem>
                  <MenuItem value="pending">Pending</MenuItem>
                </Select>
              </FormControl>
            </Grid>

            <Grid size={{ xs: 12, sm: 6, md: 3 }}   >
              <FormControl fullWidth size="small">
                <InputLabel>Environment</InputLabel>
                <Select
                  value={filters.environment || ''}
                  label="Environment"
                  onChange={(e) => handleFilterChange('environment', e.target.value)}
                >
                  <MenuItem value="">All</MenuItem>
                  <MenuItem value="development">Development</MenuItem>
                  <MenuItem value="staging">Staging</MenuItem>
                  <MenuItem value="production">Production</MenuItem>
                </Select>
              </FormControl>
            </Grid>

            <Grid size={{ xs: 12, sm: 6, md: 3 }}   >
              <FormControl fullWidth size="small">
                <InputLabel>Test Type</InputLabel>
                <Select
                  value={filters.testType || ''}
                  label="Test Type"
                  onChange={(e) => handleFilterChange('testType', e.target.value)}
                >
                  <MenuItem value="">All</MenuItem>
                  <MenuItem value="api">API</MenuItem>
                  <MenuItem value="ui">UI</MenuItem>
                  <MenuItem value="db">Database</MenuItem>
                  <MenuItem value="security">Security</MenuItem>
                  <MenuItem value="performance">Performance</MenuItem>
                </Select>
              </FormControl>
            </Grid>

            <Grid size={{ xs: 12, sm: 6, md: 3 }}   >
              <TextField
                fullWidth
                size="small"
                label="Tags"
                value={tagInput}
                onChange={(e) => setTagInput(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleAddTag()}
                placeholder="Add tag..."
              />
            </Grid>

            <Grid size={{ xs: 12, sm: 6 }}  >
              <TextField
                fullWidth
                size="small"
                label="Date From"
                type="date"
                value={filters.dateFrom || ''}
                onChange={(e) => handleFilterChange('dateFrom', e.target.value)}
                slotProps={{ inputLabel: { shrink: true } }}
              />
            </Grid>

            <Grid size={{ xs: 12, sm: 6 }}  >
              <TextField
                fullWidth
                size="small"
                label="Date To"
                type="date"
                value={filters.dateTo || ''}
                onChange={(e) => handleFilterChange('dateTo', e.target.value)}
                slotProps={{ inputLabel: { shrink: true } }}
              />
            </Grid>
          </Grid>

          {/* Tags */}
          {filters.tags && filters.tags.length > 0 && (
            <Box sx={{ mt: 2, display: 'flex', gap: 1, flexWrap: 'wrap' }}>
              {filters.tags.map((tag) => (
                <Chip
                  key={tag}
                  label={tag}
                  onDelete={() => handleRemoveTag(tag)}
                  color="secondary"
                  size="small"
                />
              ))}
            </Box>
          )}

          {/* Save Preset */}
          {onSaveFilter && (
            <Box sx={{ mt: 2, display: 'flex', gap: 1, alignItems: 'center' }}>
              <TextField
                size="small"
                placeholder="Preset name..."
                value={presetName}
                onChange={(e) => setPresetName(e.target.value)}
                sx={{ flexGrow: 1, maxWidth: 200 }}
              />
              <Button
                size="small"
                variant="outlined"
                startIcon={<Save />}
                onClick={handleSavePreset}
                disabled={!presetName.trim()}
              >
                Save Preset
              </Button>
            </Box>
          )}

          {/* Saved Presets */}
          {savedFilters.length > 0 && (
            <Box sx={{ mt: 2 }}>
              <Typography variant="caption" color="text.secondary">
                Saved Presets:
              </Typography>
              <Box sx={{ mt: 1, display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                {savedFilters.map((preset) => (
                  <Chip
                    key={preset.name}
                    label={preset.name}
                    onClick={() => handleLoadPreset(preset.config)}
                    variant="outlined"
                    size="small"
                  />
                ))}
              </Box>
            </Box>
          )}
        </Box>
      </Collapse>
    </Box>
  )
}

// Add missing Grid import
import { Grid } from '@mui/material'
