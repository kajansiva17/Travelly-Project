import React,{useMemo} from 'react'
import qrcode from 'qrcode-generator'

/* A QR code drawn as SVG from a value we generated ourselves. No network, no image file. */
export default function QrCode({value,size=190,label='QR code'}){
  const svg=useMemo(()=>{
    if(!value)return ''
    const code=qrcode(0,'M')
    code.addData(String(value))
    code.make()
    return code.createSvgTag({cellSize:4,margin:2,scalable:true})
  },[value])
  if(!value)return null
  return <div className="qr-code" role="img" aria-label={label}
    style={{width:size,height:size,background:'#fff',padding:8,borderRadius:12,border:'1px solid #cfe0f0'}}
    dangerouslySetInnerHTML={{__html:svg}}/>
}
