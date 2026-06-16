# Medical UI Component Patterns

## 1. Vital Signs Card (Material UI)
Standard card for displaying US Core Observations.

```jsx
import { Card, CardContent, Typography } from '@mui/material';

const VitalSignsCard = ({ observation }) => {
    const value = observation.valueQuantity?.value;
    const unit = observation.valueQuantity?.unit;
    const label = observation.code.coding[0].display;

    return (
        <Card sx={{ minWidth: 275, mb: 2 }}>
            <CardContent>
                <Typography color="text.secondary" gutterBottom>
                    {label}
                </Typography>
                <Typography variant="h5" component="div">
                    {value} {unit}
                </Typography>
            </CardContent>
        </Card>
    );
};
```

## 2. Risk Assessment Badge
Visual representation of risk levels.

```jsx
const RiskBadge = ({ category }) => {
    const getColor = (cat) => {
        if (cat === 'High Risk') return 'error';
        if (cat === 'Moderate Risk') return 'warning';
        return 'success';
    };

    return (
        <Chip label={category} color={getColor(category)} />
    );
};
```
