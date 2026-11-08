import {test,expect} from '@playwright/test'

for(const approved of [true,false])test(`normal login sends ${approved?'approved Admin directly to Admin':'Passenger to Passenger'} dashboard`,async({page})=>{
 const visited=[]
 await page.route('**/api/v1/**',async route=>{
  const path=new URL(route.request().url()).pathname
  let body={items:[]}
  if(path.endsWith('/auth/login'))body={access_token:'test-access',refresh_token:'test-refresh'}
  if(path.endsWith('/users/me'))body={id:'12222222-2222-4222-8222-222222222222',full_name:'Login user',account_status:'ACTIVE',approved_roles:['PASSENGER',...(approved?['ADMIN']:[])]}
  if(path.endsWith('/users/me/roles'))body={items:[{role_code:'PASSENGER',approval_status:'APPROVED'},{role_code:'ADMIN',approval_status:approved?'APPROVED':'PENDING'}]}
  await route.fulfill({json:body})
 })
 page.on('framenavigated',frame=>{if(frame===page.mainFrame())visited.push(new URL(frame.url()).pathname)})
 await page.goto('/login')
 await page.getByLabel('Email address',{exact:true}).fill('login@example.com')
 await page.getByLabel('Password',{exact:true}).fill('ExistingPassword1!')
 await page.getByRole('button',{name:'Log in',exact:true}).click()
 await expect(page).toHaveURL(new RegExp(approved?'/admin/dashboard$':'/dashboard$'))
 expect(visited).not.toContain('/account')
 if(approved)expect(visited).not.toContain('/dashboard')
})
