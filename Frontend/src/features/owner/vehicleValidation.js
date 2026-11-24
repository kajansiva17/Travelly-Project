export const vehicleTypes=['CAR','VAN','BUS','THREE_WHEELER']
export const integerFacts=['manufacture_year','seat_capacity','large_luggage_capacity','small_luggage_capacity']
export const labels={display_name:'Vehicle name',vehicle_type_code:'Vehicle type',make:'Make',model:'Model',manufacture_year:'Manufacture year',colour:'Colour',power_type:'Power type',engine_fuel_type:'Engine fuel',seat_capacity:'Usable Passenger seats',large_luggage_capacity:'Large luggage capacity',small_luggage_capacity:'Small luggage capacity',current_odometer_km:'Current odometer',transmission_type:'Transmission',air_conditioned:'Air conditioning',description:'Description',registered_owner_case:'Registered owner',registration_number:'Registration number'}
export function vehiclePayload(values){
  const result={...values}
  for(const name of integerFacts){if(!(name in result))continue;const value=result[name];if(value===''||value==null)result[name]=null;else{if(!/^[0-9]+$/.test(String(value)))throw new Error(`${labels[name]} must be a nonnegative whole number.`);result[name]=Number(value)}}
  for(const name of Object.keys(result))if(result[name]==='')result[name]=null
  if(result.air_conditioned==='true')result.air_conditioned=true
  if(result.air_conditioned==='false')result.air_conditioned=false
  if(result.power_type==='BEV')result.engine_fuel_type=null
  if(result.vehicle_type_code&&!vehicleTypes.includes(result.vehicle_type_code))throw new Error('Choose CAR, VAN, BUS or THREE_WHEELER.')
  if(result.current_odometer_km!=null&&!/^[0-9]{1,11}(\.[0-9])?$/.test(result.current_odometer_km))throw new Error('Enter the real odometer with at most one decimal place.')
  return result
}
export function validatePhoto(file){
  if(!file?.size)return 'Choose a non-empty JPEG or PNG photo.'
  if(file.size>10485760)return 'Choose a photo no larger than 10 MiB.'
  const type={jpg:'image/jpeg',jpeg:'image/jpeg',png:'image/png'}[file.name.split('.').pop().toLowerCase()]
  if(!type||(file.type&&file.type!==type))return 'Choose JPEG or PNG with a matching extension. Documents belong in private evidence.'
  return null
}
