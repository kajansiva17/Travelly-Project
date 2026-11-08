// Navigation intent only. Never send this value as an API permission or role grant.
export function journeyRole(search='') {
  const values=new URLSearchParams(search).getAll('journey')
  return values.length===1&&['owner','driver'].includes(values[0])?values[0].toUpperCase():null
}
export function journeyLink(path,role) {
  return role==='ADMIN'?`${path}?workspace=admin`:['OWNER','DRIVER'].includes(role)?`${path}?journey=${role.toLowerCase()}`:path
}
// Existing protected workspace entry, never public Admin registration or a grant.
export function authJourney(search='') {
  const q=new URLSearchParams(search),workspace=q.getAll('workspace')
  return q.has('journey')?journeyRole(search):workspace.length===1&&['owner','driver','admin'].includes(workspace[0])?workspace[0].toUpperCase():null
}
export function onboardingPath(role) { return `/${role.toLowerCase()}/onboarding` }
export function authDestination(role) { return role==='ADMIN'?'/admin/dashboard':['OWNER','DRIVER'].includes(role)?onboardingPath(role):'/dashboard' }
export function legacyApplicationRole(hash='') {
  return hash==='#owner-application'?'OWNER':hash==='#driver-application'?'DRIVER':null
}
