import { t } from '../../i18n/language.js'
import React, { useState } from 'react'
import { Button, Checkbox, Chip, FormField, FormGrid, GlassCard, InfoCallout, Input, Select, ServiceTile, Stepper } from './index'

/* Development-only gallery at /__ui-kit (not routed in production builds). */
export default function UiKitPreview() {
  const [service, setService] = useState('airport')
  const [agree, setAgree] = useState(false)
  const services = [['airport', 'car', 'Airport hire', 'One way | Return'], ['local', 'car', 'Local hire', 'One way | Return'], ['event', 'calendar', 'Event hire', 'For events, functions and special occasions'],
    ['long', 'route', 'Long distance', 'One day | Multi day'], ['ticket', 'ticket', 'Ticket booking', 'Van | Bus'], ['rent', 'key', 'Vehicle rent', 'Rent a vehicle for your own use']]
  return <main style={{ minHeight: '100vh', padding: 24, display: 'grid', gap: 20, alignContent: 'start', maxWidth: 1000, margin: '0 auto',
    background: 'var(--ui-scenic-tint), var(--ui-scenic) center / cover fixed #b7d7c8' }}>
    <h1 style={{ color: 'var(--ui-ink)' }}>{t("Travelly UI kit")}</h1>
    <GlassCard>
      <Stepper steps={['Basics', 'Features', 'Documents', 'Services', 'Review']} current={2}/>
    </GlassCard>
    <GlassCard>
      <h2 style={{ color: 'var(--ui-ink)', marginBottom: 14 }}>{t("Vehicle Basics")}</h2>
      <FormGrid columns={3}>
        <FormField label="Vehicle type" required className="ui-span-all">{({ id }) => <Select id={id}><option>{t("Other")}</option><option>{t("Van")}</option></Select>}</FormField>
        <FormField label="Plate number" required>{({ id }) => <Input id={id} placeholder="WP PA4321"/>}</FormField>
        <FormField label="Make" required>{({ id }) => <Input id={id} placeholder="Toyota"/>}</FormField>
        <FormField label="Model" required hint="Helper text">{({ id }) => <Input id={id} placeholder="Hiace"/>}</FormField>
        <FormField label="Passenger capacity" required>{({ id }) => <Input id={id} icon="seat" defaultValue="14 seats"/>}</FormField>
        <FormField label="With error" error="This field is required">{({ id, invalid }) => <Input id={id} invalid={invalid}/>}</FormField>
      </FormGrid>
      <InfoCallout className="ui-span-all">{t("New vehicle types require admin review before they can be searched and booked.")}</InfoCallout>
      <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', margin: '14px 0' }}>
        <Chip tone="success">{t("2 large bags")}</Chip><Chip tone="info" icon="globe">{t("AC required")}</Chip><Chip>{t("Default")}</Chip>
        <Chip selected={agree} onClick={() => setAgree(!agree)}>{t("Selectable")}</Chip>
      </div>
      <Checkbox checked={agree} onChange={event => setAgree(event.target.checked)}>{t("I agree to the")} <a href="#terms">{t("Terms")}</a></Checkbox>
      <div style={{ display: 'flex', gap: 12, marginTop: 16, flexWrap: 'wrap' }}>
        <Button variant="secondary" back>{t("Back")}</Button><Button disabled arrow>{t("Next (disabled)")}</Button><Button arrow>{t("Next: Vehicle Features")}</Button>
      </div>
    </GlassCard>
    <GlassCard>
      <FormGrid columns={3}>
        {services.map(([key, icon, title, description]) => <ServiceTile key={key} icon={icon} title={title} description={description} selected={service === key} onClick={() => setService(key)}/>)}
      </FormGrid>
    </GlassCard>
  </main>
}
