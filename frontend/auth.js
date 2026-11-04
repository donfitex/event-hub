import { createAuthClient } from '@neondatabase/auth';
const root=document.querySelector('#identity');
const form=document.querySelector('#auth-form');
const status=document.querySelector('#auth-status');
const csrf=form.querySelector('[name=csrfmiddlewaretoken]').value;
// The SDK talks to our fixed same-origin proxy so browser cookie restrictions do not break sessions.
const auth=createAuthClient(root.dataset.base);
const mode=root.dataset.mode;
const setStatus=(text)=>{status.textContent=text;};
async function bridge(){
  const {data,error}=await auth.token();
  if(error || !data?.token) throw new Error(error?.message || 'Please verify your email, then log in.');
  const response=await fetch('/identity/exchange/',{method:'POST',headers:{'Content-Type':'application/json','X-CSRFToken':csrf},body:JSON.stringify({token:data.token,next:root.dataset.next})});
  const result=await response.json();
  if(!response.ok) throw new Error(result.error);
  window.location.assign(result.next);
}
// Neon adapter fetch options belong on individual calls. They include CSRF on same-origin proxy POSTs.
const fetchOptions={headers:{'X-CSRFToken':csrf}};
document.querySelector('#name-field').hidden=mode!=='signup';
if(mode==='new-password'){document.querySelector('#auth-email').required=false;document.querySelector('#auth-email').parentElement.hidden=true;}
if(mode==='reset') {document.querySelector('#auth-password').required=false;document.querySelector('#auth-password').parentElement.hidden=true;}
if(mode==='logout'){
  form.hidden=true;
  auth.signOut({fetchOptions}).then(({error})=>{if(error)throw new Error(error.message);window.location.assign('/');}).catch(error=>setStatus(error.message));
} else {
  form.addEventListener('submit',async(event)=>{
    event.preventDefault();
    const button=form.querySelector('button');button.disabled=true;setStatus('Working…');
    const values=new FormData(form);
    try{
      let response;
      if(mode==='signup') response=await auth.signUp.email({email:values.get('email'),password:values.get('password'),name:values.get('name')||'EventHub attendee',fetchOptions});
      else if(mode==='reset') response=await auth.requestPasswordReset({email:values.get('email'),redirectTo:window.location.origin+'/identity/?mode=new-password',fetchOptions});
      else if(mode==='new-password') response=await auth.resetPassword({newPassword:values.get('password'),token:new URLSearchParams(window.location.search).get('token'),fetchOptions});
      else response=await auth.signIn.email({email:values.get('email'),password:values.get('password'),fetchOptions});
      if(response.error) throw new Error(response.error.message || 'Please try again.');
      if(mode==='reset'){setStatus('If this account exists, check your email for the next step.');return;}
      if(mode==='new-password'){window.location.assign('/identity/?mode=login');return;}
      await bridge();
    }catch(error){setStatus(error.message || 'Unable to sign in. Please try again.');}
    finally{button.disabled=false;button.textContent='Continue ↗';}
  });
}
