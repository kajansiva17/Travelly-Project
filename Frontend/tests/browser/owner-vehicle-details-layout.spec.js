import {test,expect} from '@playwright/test'
import {visit} from './helpers/redesign.js'

const vehicle={
  id:'vehicle-one',reference:'VH-001',label:'Toyota Hiace NC-1234',registration_number:'NC-1234',registration_locked:false,
  verification_status:'APPROVED',availability_status:'ACTIVE',published:false,version:4,documents:[],photos:[],checklist:[],
  vehicle_type_code:'VAN',make:'Toyota',model:'Hiace',manufacture_year:2022,colour:'White',power_type:'ICE',engine_fuel_type:'DIESEL',
  seat_capacity:12,large_luggage_capacity:4,small_luggage_capacity:8,current_odometer_km:'25000.0',transmission_type:'Automatic',
  air_conditioned:true,registered_owner_case:'SELF',description:'',hire_location:{base_label:'Colombo',base_configured:true,pickup_distance_km:'50.00',accepts_bookings:true,current_observed_at:'2026-11-18T06:00:00Z'}
}

async function openDetails(page){
  await page.route('**/api/v1/**',route=>{
    const request=route.request(),path=new URL(request.url()).pathname.replace('/api/v1','')
    if(path==='/auth/login')return route.fulfill({json:{access_token:'layout-access',refresh_token:'layout-refresh',expires_in:900}})
    if(path==='/auth/config')return route.fulfill({json:{google_enabled:false}})
    if(path==='/users/me')return route.fulfill({json:{id:'owner-one',full_name:'Layout Owner',account_status:'ACTIVE',email:'owner@example.com',email_verified_at:'2026-11-01T00:00:00Z',approved_roles:['PASSENGER','OWNER']}})
    if(path==='/users/me/roles')return route.fulfill({json:{items:[{role_code:'PASSENGER',approval_status:'APPROVED'},{role_code:'OWNER',approval_status:'APPROVED'}]}})
    if(path==='/owners/me/vehicles/vehicle-one')return route.fulfill({json:vehicle})
    return route.fulfill({json:{items:[]}})
  })
  await page.goto('/login')
  await page.getByLabel('Email address',{exact:true}).fill('owner@example.com')
  await page.getByLabel('Password',{exact:true}).fill('BrowserTravelly1!')
  await page.getByRole('button',{name:'Log in',exact:true}).click()
  await expect(page).toHaveURL(/\/dashboard$/)
  await page.setViewportSize({width:1280,height:585})
  await visit(page,'/owner/vehicles/vehicle-one')
  await expect(page.getByRole('list',{name:'Details',exact:true})).toBeVisible()
}

async function expectFits(page){
  const result=await page.locator('.flow-card').evaluate(card=>{
    const footer=card.querySelector(':scope > .flow-actions'),pane=card.querySelector('.vehicle-detail-pane:not([hidden])')
    const f=footer.getBoundingClientRect(),p=pane.getBoundingClientRect()
    return {cardScroll:card.scrollHeight-card.clientHeight,documentScroll:document.documentElement.scrollHeight-innerHeight,footerBottom:f.bottom,paneBottom:p.bottom,footerTop:f.top,viewport:innerHeight}
  })
  expect(result.cardScroll).toBeLessThanOrEqual(1)
  expect(result.documentScroll).toBeLessThanOrEqual(1)
  expect(result.footerBottom).toBeLessThanOrEqual(result.viewport)
  expect(result.paneBottom).toBeLessThanOrEqual(result.footerTop)
}

test('Owner Details uses one fitted location flow in English, Tamil and Sinhala',async({page},info)=>{
  test.setTimeout(90000)
  await openDetails(page)
  const languages=[
    ['en',['Vehicle details 1','Vehicle details 2','Location & bookings','Current vehicle location']],
    ['ta',['வாகன விவரங்கள் 1','வாகன விவரங்கள் 2','இருப்பிடம் மற்றும் முன்பதிவுகள்','வாகனத்தின் தற்போதைய இருப்பிடம்']],
    ['si',['වාහන විස්තර 1','වාහන විස්තර 2','ස්ථානය සහ වෙන්කිරීම්','වාහනයේ වත්මන් ස්ථානය']]
  ]
  for(const [language,steps] of languages){
    await page.locator('.site-header select').first().selectOption(language)
    for(const label of steps)await expect(page.getByRole('button',{name:new RegExp(label)})).toBeVisible()
    for(let index=0;index<steps.length;index++){
      await page.getByRole('button',{name:new RegExp(steps[index])}).click()
      await expectFits(page)
      await page.screenshot({path:info.outputPath(`owner-details-${language}-${index+1}.png`)})
    }
  }
})

test('Details navigation preserves unsaved facts and location controls without duplicates',async({page})=>{
  await openDetails(page)
  const make=page.getByRole('textbox',{name:/^Make .*Required for submission/})
  await make.fill('Unsaved make')
  await page.getByRole('button',{name:/Vehicle details 2/}).click()
  await page.getByRole('button',{name:/Vehicle details 1/}).click()
  await expect(make).toHaveValue('Unsaved make')
  await page.getByRole('button',{name:/Location & bookings/}).click()
  const distance=page.getByRole('spinbutton',{name:/Pickup distance/})
  await expect(distance).toHaveCount(1)
  await expect(page.getByLabel('Accept new hire bookings',{exact:true})).toHaveCount(1)
  await distance.fill('65')
  await page.getByLabel('Accept new hire bookings',{exact:true}).uncheck()
  await page.getByRole('button',{name:/Current vehicle location/}).click()
  await expect(page.getByRole('searchbox',{name:/Confirm where the vehicle is now/})).toHaveCount(1)
  await page.getByRole('button',{name:/Location & bookings/}).click()
  await expect(distance).toHaveValue('65')
  await expect(page.getByLabel('Accept new hire bookings',{exact:true})).not.toBeChecked()
})
