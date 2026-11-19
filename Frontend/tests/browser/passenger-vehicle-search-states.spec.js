import { test, expect } from '@playwright/test'

const serviceId='32222222-2222-4222-8222-222222222222'
const A={label:'Colombo Fort',latitude:'6.933759',longitude:'79.850002',token:'a'.repeat(43)}
const B={label:'Kandy',latitude:'7.295500',longitude:'80.635600',token:'b'.repeat(43)}
const draft={
  service:'local',serviceTypeId:serviceId,services:[{id:serviceId,name:'Local hire',pricing_scope:'LOCAL'}],
  detail:{date:'2027-01-10',time:'09:00',pickupPlace:A,destinationPlace:B,journey:'ONE_WAY'},
  requirements:{passengers:'2',largeLuggage:'0',smallLuggage:'0'},
}

test('Passenger vehicle search keeps loading, failure, empty and result states distinct and retryable',async({page})=>{
  let mode='waiting',release
  await page.addInitScript(value=>sessionStorage.setItem('travelly.passenger.booking-draft.v2',JSON.stringify(value)),draft)
  await page.route('**/api/v1/search/vehicles',async route=>{
    if(mode==='waiting')await new Promise(resolve=>{release=resolve})
    if(mode==='failure')return route.fulfill({status:503,json:{code:'ROUTING_UNAVAILABLE',message:'A trustworthy route price is unavailable. Please try again.'}})
    if(mode==='empty')return route.fulfill({json:{items:[],quote_on_request:[]}})
    return route.fulfill({json:{
      items:[{id:'available',reference:'VEH-AVAILABLE',make:'Ready',model:'Van',passenger_seats:4,large_luggage:2,distance_km:3.2}],
      quote_on_request:[{id:'confirm',reference:'VEH-CONFIRM',make:'Confirm',model:'Van',passenger_seats:4,large_luggage:2,owner_confirmation_required:true,feasibility_code:'VEHICLE_LOCATION_STALE'}],
    }})
  })

  await page.goto('/travel/book/vehicles')
  await expect(page.getByRole('heading',{name:'Checking matching vehicles',exact:true})).toBeVisible()
  mode='failure';release()
  await expect(page.getByRole('heading',{name:'Vehicle search could not be completed',exact:true})).toBeVisible()
  await expect(page.getByText('A trustworthy route price is unavailable. Please try again.',{exact:true})).toBeVisible()
  await expect(page.getByRole('heading',{name:'No matching vehicle is currently available',exact:true})).toHaveCount(0)

  mode='empty'
  await page.getByRole('button',{name:'Retry vehicle search',exact:true}).click()
  await expect(page.getByRole('heading',{name:'No matching vehicle is currently available',exact:true})).toBeVisible()
  await expect(page.getByRole('heading',{name:'Vehicle search could not be completed',exact:true})).toHaveCount(0)

  mode='results'
  await page.reload()
  await expect(page.getByRole('button',{name:'Select vehicle',exact:true})).toBeVisible()
  await page.getByRole('button',{name:'Next page',exact:true}).click()
  await expect(page.getByRole('heading',{name:'Owner confirmation required',exact:true})).toBeVisible()
  await expect(page.getByRole('button',{name:'Request Owner confirmation',exact:true})).toBeVisible()
  await expect(page.getByRole('heading',{name:'No matching vehicle is currently available',exact:true})).toHaveCount(0)
})
