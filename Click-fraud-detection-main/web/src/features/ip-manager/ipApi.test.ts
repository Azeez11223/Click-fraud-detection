import { describe, expect, it, vi } from 'vitest'
import { isValidIp, uploadDataset } from './ipApi'

describe('IP address validation', () => {
  it.each(['192.168.1.1','0.0.0.0','2001:db8::1','::1'])('accepts %s', (value) => expect(isValidIp(value)).toBe(true))
  it.each(['256.1.1.1','1.2.3','abc','2001:::1','gggg::1'])('rejects %s', (value) => expect(isValidIp(value)).toBe(false))
})

describe('dataset upload', () => {
  it('sends multipart file and list_type and reports the result', async () => {
    const send = vi.fn(function(this: XMLHttpRequest) { Object.defineProperty(this, 'status', { value: 200 }); Object.defineProperty(this, 'responseText', { value: JSON.stringify({ total_ips: 1000, inserted_to_list: 998, skipped: 2, invalid: 0 }) }); this.onload?.(new ProgressEvent('load')) })
    vi.stubGlobal('XMLHttpRequest', class { upload={onprogress:null as ((e:ProgressEvent)=>void)|null}; status=0; responseText=''; onload: ((e:ProgressEvent)=>void)|null=null; onerror:(()=>void)|null=null; open=vi.fn(); setRequestHeader=vi.fn(); send=send })
    const progress=vi.fn(); await expect(uploadDataset(new File(['1.2.3.4'], 'ips.txt'), 'block', progress)).resolves.toMatchObject({total_ips:1000,inserted_to_list:998})
    expect(send).toHaveBeenCalledOnce()
    vi.unstubAllGlobals()
  })
})
