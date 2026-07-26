import { Box, Typography, Card, CardContent, CardActionArea, Chip, Stack, Link, Divider, Alert } from '@mui/material'
import {
  Gavel as GavelIcon,
  School as SchoolIcon,
  Security as SecurityIcon,
  Description as DescriptionIcon,
  Policy as PolicyIcon,
  BugReport as BugReportIcon,
  Inventory as InventoryIcon,
} from '@mui/icons-material'
import DisclosureBanner from '../components/common/DisclosureBanner'

/**
 * Compliance Center — EU AI Act + Cyber Resilience Act
 *
 * Centralizes all compliance documentation for SabaTech/QA-FRAMEWORK.
 * Accessible to authenticated users from the main navigation.
 *
 * Regulatory basis:
 * - EU AI Act (Regulation 2024/1689) — G1-G4 deliverables
 * - Cyber Resilience Act (Regulation 2024/2847) — CRA-1/2
 */
export default function Compliance() {
  const complianceDocs = [
    {
      title: 'AI Systems Register (GPAI Inventory)',
      description: 'Group-wide inventory of 20 GPAI models used across SabaTech. Required by EU AI Act Art. 53.',
      icon: <InventoryIcon />,
      chip: 'G3 — Art. 53',
      chipColor: 'success' as const,
      href: 'https://github.com/SabaTech-dev/QA-FRAMEWORK/blob/main/docs/compliance/ai-systems-register.md',
    },
    {
      title: 'GPAI Inventory (QA-FRAMEWORK)',
      description:
        'Authoritative QA-FRAMEWORK-scoped GPAI model inventory (Art. 53-55). Consolidates and supersedes the legacy AI_SYSTEMS_INVENTORY.md.',
      icon: <DescriptionIcon />,
      chip: 'G3 — Product',
      chipColor: 'success' as const,
      href: 'https://github.com/SabaTech-dev/QA-FRAMEWORK/blob/main/docs/compliance/GPAI-Inventory.md',
    },
    {
      title: 'AI Literacy Policy',
      description: 'Article 4 AI literacy requirements. Covers staff competencies, training plan, and role assessment.',
      icon: <SchoolIcon />,
      chip: 'G4 — Art. 4',
      chipColor: 'info' as const,
      href: 'https://github.com/SabaTech-dev/QA-FRAMEWORK/blob/main/docs/compliance/AI_LITERACY_POLICY.md',
    },
    {
      title: 'Art. 50(1) Transparency Assessment',
      description: 'Assessment of whether QA-FRAMEWORK interacts directly with persons. Conclusion: not applicable, but best-practice disclosure implemented.',
      icon: <GavelIcon />,
      chip: 'G1 — Art. 50(1)',
      chipColor: 'warning' as const,
      href: 'https://github.com/SabaTech-dev/QA-FRAMEWORK/blob/main/docs/compliance/art-50-1-assessment.md',
    },
    {
      title: 'Coordinated Vulnerability Disclosure (CVD) Policy',
      description: 'CRA Art. 13 vulnerability handling and disclosure framework. SLAs, safe harbor, reporting channels.',
      icon: <BugReportIcon />,
      chip: 'CRA-1 — Art. 13',
      chipColor: 'error' as const,
      href: 'https://github.com/SabaTech-dev/QA-FRAMEWORK/blob/main/docs/compliance/cvd-policy.md',
    },
    {
      title: 'Incident Reporting Procedure',
      description: 'CRA Art. 14 three-stage incident reporting (24h → 72h → 1 month). Templates, roles, CSIRT contacts.',
      icon: <SecurityIcon />,
      chip: 'CRA-2 — Art. 14',
      chipColor: 'error' as const,
      href: 'https://github.com/SabaTech-dev/QA-FRAMEWORK/blob/main/docs/compliance/incident-reporting-procedure.md',
    },
    {
      title: 'NIST CSF 2.0 Governance',
      description: 'Security governance docs aligned with NIST Cybersecurity Framework 2.0.',
      icon: <PolicyIcon />,
      chip: 'Security',
      chipColor: 'default' as const,
      href: 'https://github.com/SabaTech-dev/QA-FRAMEWORK/tree/main/docs/security',
    },
  ]

  return (
    <Box sx={{ p: 3, maxWidth: 1200, mx: 'auto' }}>
      <DisclosureBanner />

      <Typography variant="h4" gutterBottom sx={{ fontWeight: 700 }}>
        Compliance Center
      </Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
        EU AI Act (Regulation 2024/1689) and Cyber Resilience Act (Regulation 2024/2847) compliance documentation.
      </Typography>

      <Alert severity="info" sx={{ mb: 3 }}>
        <Typography variant="body2">
          <strong>QA-FRAMEWORK classification:</strong> Limited Risk under EU AI Act.
          Deadline for Sprint 1 compliance: <strong>2 August 2026</strong>.
        </Typography>
      </Alert>

      <Divider sx={{ mb: 3 }}>
        <Chip label="Compliance Documents" color="primary" variant="outlined" />
      </Divider>

      <Stack spacing={2}>
        {complianceDocs.map((doc) => (
          <Card key={doc.title} variant="outlined">
            <CardActionArea component={Link} href={doc.href} target="_blank" rel="noopener noreferrer">
              <CardContent sx={{ display: 'flex', alignItems: 'flex-start', gap: 2 }}>
                <Box sx={{ color: 'primary.main', mt: 0.5 }}>{doc.icon}</Box>
                <Box sx={{ flex: 1 }}>
                  <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 0.5 }}>
                    <Typography variant="subtitle1" component="span" sx={{ fontWeight: 600 }}>
                      {doc.title}
                    </Typography>
                    <Chip label={doc.chip} size="small" color={doc.chipColor} variant="outlined" />
                  </Stack>
                  <Typography variant="body2" color="text.secondary">
                    {doc.description}
                  </Typography>
                </Box>
              </CardContent>
            </CardActionArea>
          </Card>
        ))}
      </Stack>

      <Divider sx={{ my: 3 }}>
        <Chip label="Sprint 1 Status" color="primary" />
      </Divider>

      <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
        <Chip label="G1: AI Disclosure Banner ✅" color="success" variant="filled" />
        <Chip label="G3: GPAI Inventory ✅" color="success" variant="filled" />
        <Chip label="G4: AI Literacy Policy ✅" color="success" variant="filled" />
        <Chip label="CRA-1: CVD Policy ✅" color="success" variant="filled" />
        <Chip label="CRA-2: Incident Reporting ✅" color="success" variant="filled" />
      </Stack>
    </Box>
  )
}
