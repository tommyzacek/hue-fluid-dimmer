/* Isolated config-flow selector. Does not patch Home Assistant components. */
class HrcLuxSelector extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({mode: 'open'});
    this.shadowRoot.innerHTML = `<style>
      :host{display:block;color:var(--primary-text-color);font:inherit}
      label{display:block;margin-bottom:12px} .row{display:flex;align-items:center;gap:16px}
      input{flex:1;min-width:0;accent-color:var(--primary-color);height:32px}
      output{flex:0 0 76px;min-width:76px;white-space:nowrap;text-align:right;font-size:18px;font-variant-numeric:tabular-nums}
      .limits{display:flex;justify-content:space-between;color:var(--secondary-text-color);font-size:12px;margin-right:92px}
      .reading{margin-top:8px;color:var(--secondary-text-color);font-size:13px}
    </style><label for="lux"></label><div class="row"><input id="lux" type="range" min="0" max="660" step="1"><output for="lux"></output></div><div class="limits"><span>0 lx</span><span>650 lx · ∞</span></div><div class="reading" aria-live="polite"></div>`;
    const warning = document.createElement('div');
    warning.className = 'warning';
    warning.style.cssText = 'color:var(--error-color,#db4437);font-weight:bold;margin:8px 0';
    this.shadowRoot.querySelector('label').after(warning);
    this.slider = this.shadowRoot.querySelector('input');
    this.slider.addEventListener('input', () => {
      this._value = this.valueFromSlider(Number(this.slider.value));
      this.refresh();
      this.dispatchEvent(new CustomEvent('value-changed', {detail:{value:this._value},bubbles:true,composed:true}));
    });
    this.slider.addEventListener('change', event => event.stopPropagation());
  }
  valueFromSlider(value){return value;}
  set hass(value){this._hass=value;this.refresh();}
  set selector(value){this._selector=value;this.refresh();}
  set value(value){this._value=value;this.refresh();}
  get value(){return this._value;}
  set label(value){this._label=value;this.refresh();}
  set disabled(value){this._disabled=value;this.refresh();}
  set required(value){this._required=value;this.refresh();}
  reportValidity(){return Number.isFinite(this._value) && this._value>=0 && this._value<=660;}
  focus(){this.slider.focus();}
  refresh(){
    if(!this.slider)return;
    const value=this._value??660;
    const text=value>650?'∞':`${value} lx`;
    this.slider.value=String(value);
    this.slider.disabled=!!this._disabled;
    this.slider.setAttribute('aria-valuetext',text);
    this.shadowRoot.querySelector('label').textContent=this._label||'Illuminance';
    this.shadowRoot.querySelector('output').textContent=text;
    const language=this._hass?.language||'en';
    const labels=language.startsWith('cs')?['Aktuální osvětlení','Při tomto osvětlení a nastavení prahu se světla ','ZAPNOU','NEZAPNOU','Výsledek nelze vyhodnotit – měření není dostupné.']:language.startsWith('sk')?['Aktuálne osvetlenie','Pri tomto osvetlení a nastavení prahu sa svetlá ','ZAPNÚ','NEZAPNÚ','Výsledok nemožno vyhodnotiť – meranie nie je dostupné.']:['Current illuminance','At this illuminance and threshold, the lights will turn ','ON','OFF','Cannot evaluate – the reading is unavailable.'];
    const entity=this._selector?.hrc_lux?.entity;
    const state=this._hass?.states?.[entity]?.state;
    const current=state!=null && state!=='' && Number.isFinite(Number(state)) ? `${new Intl.NumberFormat(language,{maximumFractionDigits:1}).format(Number(state))} lx`:'—';
    const disabled=this._hass?.states?.[this._selector?.hrc_lux?.enabled_entity]?.state==='off';
    const warning=this.shadowRoot.querySelector('.warning');
    warning.hidden=!disabled;
    warning.textContent=language.startsWith('cs')?'Senzor osvětlení je vypnutý v oficiální integraci Hue. Pro použití této funkce jej zapněte.':language.startsWith('sk')?'Senzor osvetlenia je vypnutý v oficiálnej integrácii Hue. Ak chcete používať túto funkciu, zapnite ho.':'The illuminance sensor is disabled in the official Hue integration. Enable it to use this feature.';
    const enabledEntity=this._selector?.hrc_lux?.enabled_entity;
    const enabledState=this._hass?.states?.[enabledEntity]?.state;
    const valid=current!=='—' && (!enabledEntity || enabledState==='on');
    const result=value>650?true:(valid?Number(state)<value:null);
    const reading=this.shadowRoot.querySelector('.reading');
    reading.style.fontWeight='bold';
    reading.replaceChildren(document.createTextNode(`${labels[0]}: ${valid?current:'—'} · `));
    if(result===null){
      reading.append(document.createTextNode(labels[4]));
    }else{
      reading.append(document.createTextNode(labels[1]));
      const outcome=document.createElement('span');
      outcome.textContent=labels[result?2:3];
      outcome.style.color=result?'var(--success-color,#43a047)':'var(--error-color,#db4437)';
      reading.append(outcome,document.createTextNode('.'));
    }
  }
}
if(!customElements.get('ha-selector-hrc_lux'))customElements.define('ha-selector-hrc_lux',HrcLuxSelector);

class HrcSensitivitySelector extends HrcLuxSelector {
  constructor() {
    super();
    this.slider.id = 'sensitivity';
    this.slider.min = '0';
    this.slider.max = '2';
    this.slider.step = '1';
    this.shadowRoot.querySelector('label').htmlFor = 'sensitivity';
    this.shadowRoot.querySelector('output').htmlFor = 'sensitivity';
    this.shadowRoot.querySelector('.limits').innerHTML = '<span>│</span><span>│</span><span>│</span>';
  }
  reportValidity(){return Number.isInteger(this._value) && this._value>=0 && this._value<=2;}
  refresh(){
    if(!this.slider)return;
    const language=this._hass?.language||'en';
    const labels=language.startsWith('cs')?['Nízká','Střední','Vysoká']:language.startsWith('sk')?['Nízka','Stredná','Vysoká']:['Low','Medium','High'];
    const value=this._value??1;
    const text=labels[value]??'—';
    this.slider.value=String(value);
    this.slider.disabled=!!this._disabled;
    this.slider.setAttribute('aria-valuetext',text);
    this.shadowRoot.querySelector('label').textContent=this._label||'Motion sensitivity';
    this.shadowRoot.querySelector('output').textContent=text;
    this.shadowRoot.querySelector('.reading').hidden=true;
  }
}
if(!customElements.get('ha-selector-hrc_sensitivity'))customElements.define('ha-selector-hrc_sensitivity',HrcSensitivitySelector);

class HrcMotionEnabled extends HTMLElement {
  constructor(){
    super();this.attachShadow({mode:'open'});
    this.shadowRoot.innerHTML=`<style>:host{display:block;color:var(--primary-text-color)}.row{display:flex;align-items:center;justify-content:space-between;gap:16px}.warning{color:var(--error-color,#db4437);font-weight:bold;margin-top:8px}</style><div class="row"><label></label><ha-switch></ha-switch></div><div class="warning"></div>`;
    this.control=this.shadowRoot.querySelector('ha-switch');
    this.control.addEventListener('change',event=>{event.stopPropagation();this._value=this.control.checked;this.dispatchEvent(new CustomEvent('value-changed',{detail:{value:this._value},bubbles:true,composed:true}));});
    this.shadowRoot.querySelector('label').addEventListener('click',()=>{if(!this._disabled){this.control.click();}});
  }
  set hass(value){this._hass=value;this.refresh();}
  set selector(value){this._selector=value;this.refresh();}
  set value(value){this._value=value;this.refresh();}
  get value(){return this._value;}
  set label(value){this._label=value;this.refresh();}
  set disabled(value){this._disabled=value;this.refresh();}
  reportValidity(){return typeof this._value==='boolean';}
  refresh(){
    if(!this.control)return;
    this.control.checked=!!this._value;this.control.disabled=!!this._disabled;
    this.shadowRoot.querySelector('label').textContent=this._label||'Enable control';
    this.control.setAttribute('aria-label',this._label||'Enable control');
    const warning=this.shadowRoot.querySelector('.warning');
    warning.hidden=this._hass?.states?.[this._selector?.hrc_motion_enabled?.entity]?.state!=='off';
    const language=this._hass?.language||'en';
    warning.textContent=language.startsWith('cs')?'Pohybový senzor je vypnutý v oficiální integraci Hue. Pro použití ovládání pohybem jej zapněte.':language.startsWith('sk')?'Pohybový senzor je vypnutý v oficiálnej integrácii Hue. Ak chcete používať ovládanie pohybom, zapnite ho.':'The motion sensor is disabled in the official Hue integration. Enable it to use motion control.';
  }
}
if(!customElements.get('ha-selector-hrc_motion_enabled'))customElements.define('ha-selector-hrc_motion_enabled',HrcMotionEnabled);

// Keep HA's native colored temperature bar, snapping only this instance to 100 K.
class HrcTemperatureSelector extends HTMLElement {
  constructor(){
    super();this.attachShadow({mode:'open'});
    this.control=document.createElement('ha-selector');
    this.shadowRoot.append(this.control);
    this.control.addEventListener('value-changed',event=>{
      event.stopPropagation();this.commit(Number(event.detail.value));
    });
    this.control.addEventListener('keydown',event=>{
      const delta={ArrowLeft:-100,ArrowDown:-100,ArrowRight:100,ArrowUp:100}[event.key];
      if(delta===undefined && event.key!=='Home' && event.key!=='End')return;
      event.preventDefault();event.stopPropagation();
      this.commit(event.key==='Home'?1500:event.key==='End'?10000:(this._value??2700)+delta);
    },true);
  }
  async commit(value){
    if(this._disabled || !Number.isFinite(value))return;
    const revision=this._revision=(this._revision||0)+1;
    this.control.value=value;
    await this.control.updateComplete;
    if(revision!==this._revision)return;
    this._value=Math.max(1500,Math.min(10000,Math.round(value/100)*100));
    this.refresh();
    this.dispatchEvent(new CustomEvent('value-changed',{detail:{value:this._value},bubbles:true,composed:true}));
  }
  set hass(value){this._hass=value;this.refresh();}
  set value(value){this._value=value;this.refresh();}
  get value(){return this._value;}
  set label(value){this._label=value;this.refresh();}
  set disabled(value){this._disabled=value;this.refresh();}
  set required(value){this._required=value;this.refresh();}
  reportValidity(){return Number.isFinite(this._value) && this._value>=1500 && this._value<=10000;}
  refresh(){
    if(!this.control)return;
    this.control.selector={color_temp:{unit:'kelvin',min:1500,max:10000}};
    this.control.hass=this._hass;
    this.control.value=this._value==null?2700:Math.round(this._value/100)*100;
    this.control.label=this._label;
    this.control.disabled=!!this._disabled;
    this.control.required=!!this._required;
    this.configureStep();
  }
  async configureStep(){
    await customElements.whenDefined('ha-selector-color_temp');
    await this.control.updateComplete;
    const temperature=this.control.shadowRoot?.querySelector('ha-selector-color_temp');
    if(!temperature)return;
    await temperature.updateComplete;
    const slider=temperature.shadowRoot?.querySelector('ha-labeled-slider');
    if(slider)slider.step=100;
  }
}
if(!customElements.get('ha-selector-hrc_temperature'))customElements.define('ha-selector-hrc_temperature',HrcTemperatureSelector);

class HrcTimeoutSelector extends HrcLuxSelector {
  constructor(){
    super();
    this.slider.min='0';this.slider.max='68';this.slider.step='1';
    this.shadowRoot.querySelector('.reading').hidden=true;
    this.shadowRoot.querySelector('.warning').hidden=true;
    this.refresh();
  }
  valueFromSlider(index){return index<=18?60+index*30:600+(index-18)*60;}
  reportValidity(){return Number.isFinite(this._value)&&this._value>=60&&this._value<=3600&&this._value%(this._value<=600?30:60)===0;}
  refresh(){
    if(!this.slider)return;
    const raw=this._value??300;
    const step=raw<=600?30:60;
    const value=Math.max(60,Math.min(3600,Math.round(raw/step)*step));
    const language=this._hass?.language||'en';
    const text=`${new Intl.NumberFormat(language,{maximumFractionDigits:1}).format(value/60)} min`;
    this.slider.value=String(value<=600?(value-60)/30:18+(value-600)/60);
    this.slider.disabled=!!this._disabled;
    this.slider.setAttribute('aria-valuetext',text);
    this.shadowRoot.querySelector('label').textContent=this._label||'Timeout';
    this.shadowRoot.querySelector('output').textContent=text;
    const limits=this.shadowRoot.querySelectorAll('.limits span');
    limits[0].textContent='1 min';limits[1].textContent='60 min';
  }
}
if(!customElements.get('ha-selector-hrc_timeout'))customElements.define('ha-selector-hrc_timeout',HrcTimeoutSelector);

// Motion period editor: HA owns entity/color selectors; times partition the day.
class HrcMotionPeriods extends HTMLElement {
  constructor(){super();this.attachShadow({mode:'open'});this._value=[];this.openIds=new Set();}
  connectedCallback(){this._stopStyling=hrcOutlineMotionForm(this);}
  disconnectedCallback(){this._stopStyling?.();}
  set hass(value){const language=this._hass?.language;this._hass=value;if(language!==value?.language)this.render();else for(const control of this.shadowRoot.querySelectorAll('ha-selector'))control.hass=value;}
  set value(value){const next=Array.isArray(value)?structuredClone(value):[];if(JSON.stringify(next)===JSON.stringify(this._value))return;this._value=next;if(!this.initialized&&next.length){this.openIds.add(next[0].id);this.initialized=true;}this.render();}
  get value(){return this._value;}
  set selector(value){this._selector=value;}
  set label(value){if(this._label===value)return;this._label=value;this.render();}
  set disabled(value){if(this._disabled===value)return;this._disabled=value;this.render();}
  set required(value){this._required=value;}
  reportValidity(){
    const times=this._value.map(p=>p.start);
    return times.length>0&&new Set(times).size===times.length&&this._value.every(p=>/^([01]\d|2[0-3]):[0-5]\d$/.test(p.start)&&((p.do_not_disturb)||(!p.override_targets||p.targets.length>0)));
  }
  emit(){this.dispatchEvent(new CustomEvent('value-changed',{detail:{value:structuredClone(this._value)},bubbles:true,composed:true}));}
  text(){const lang=this._hass?.language||'en';return lang.startsWith('cs')?{
    title:'Vyhrazené časy',all:'Celý den',add:'Přidat časový blok',remove:'Odstranit blok',start:'Začátek',quiet:'Nerušit',quietNote:'Nezahajuje nové cykly. Již běžící cyklus dokončí.',brightness:'Jas',previous:'Předchozí stav',configured:'Nastavené %',percent:'Nastavený jas',color:'Barva světla',unchanged:'Ponechat beze změny',temperature:'Teplota bílé',rgb:'Vlastní barva',timeout:'Zhasnout po době bez pohybu',override:'Použít v tomto čase jiná světla',targets:'Cílová světla',duplicate:'Každý blok musí začínat v jiný čas.',help:'Předchozí stav obnoví jas před závěrečným ztlumením Motionu. Změny jasu během cyklu se zohlední, změny mimo cyklus se nepřebírají. Barva se nastavuje samostatně.'
  }:lang.startsWith('sk')?{
    title:'Vyhradené časy',all:'Celý deň',add:'Pridať časový blok',remove:'Odstrániť blok',start:'Začiatok',quiet:'Nerušiť',quietNote:'Nezačína nové cykly. Už prebiehajúci cyklus dokončí.',brightness:'Jas',previous:'Predchádzajúci stav',configured:'Nastavené %',percent:'Nastavený jas',color:'Farba svetla',unchanged:'Ponechať bez zmeny',temperature:'Teplota bielej',rgb:'Vlastná farba',timeout:'Zhasnúť po čase bez pohybu',override:'Použiť v tomto čase iné svetlá',targets:'Cieľové svetlá',duplicate:'Každý blok musí začínať v inom čase.',help:'Predchádzajúci stav obnoví jas pred záverečným stlmením Motionu. Ak svetlo medzitým rozsvietite inak, použije sa jeho novší stav. Farba sa nastavuje samostatne.'
  }:{title:'Dedicated times',all:'All day',add:'Add time period',remove:'Remove period',start:'Starts at',quiet:'Do not disturb',quietNote:'Does not start new cycles. A running cycle can finish.',brightness:'Brightness',previous:'Previous state',configured:'Configured %',percent:'Configured brightness',color:'Light color',unchanged:'Leave unchanged',temperature:'White temperature',rgb:'Custom color',timeout:'Turn off after no motion for',override:'Use different lights during this period',targets:'Target lights',duplicate:'Each period must have a different start time.',help:'Previous state restores brightness from before Motion’s final dimming. If the light was turned on elsewhere in between, its newer state takes precedence. Color is configured separately.'};}
  add(){
    const list=[...this._value].sort((a,b)=>a.start.localeCompare(b.start));let best=-1,at=0;
    for(let i=0;i<list.length;i++){const [h,m]=list[i].start.split(':').map(Number),a=h*60+m;const [nh,nm]=list[(i+1)%list.length].start.split(':').map(Number);let gap=(nh*60+nm-a+1440)%1440;if(list.length===1)gap=1440;if(gap>best){best=gap;at=(a+Math.floor(gap/2))%1440;}}
    if(best<2)return;
    const base=structuredClone(list[0]||{startup:{brightness:'unchanged',percentage:50,color:'unchanged',temperature:2700,rgb:[255,180,100]},timeout:300,targets:[],override_targets:false});
    base.id=`period-${Date.now().toString(36)}-${Math.random().toString(36).slice(2,10)}`;base.start=`${String(Math.floor(at/60)).padStart(2,'0')}:${String(at%60).padStart(2,'0')}`;base.do_not_disturb=false;this._value.push(base);this.openIds.add(base.id);this.emit();this.render();
  }
  render(){
    if(!this.shadowRoot)return;const t=this.text();this.shadowRoot.replaceChildren();
    const style=document.createElement('style');style.textContent=`:host{display:block;color:var(--primary-text-color);font:inherit}h3{font-size:16px;font-weight:500;margin:8px 0 16px}details{border:1px solid var(--divider-color,#ddd);border-radius:12px;margin:12px 0}summary{cursor:pointer;padding:16px;font-weight:600}.body{padding:0 16px 16px;display:grid;gap:20px}.row{display:flex;align-items:center;gap:12px}.row span:first-child{flex:1}.end,.note{color:var(--secondary-text-color);font-size:13px}.note{line-height:1.5}.field{display:grid;gap:8px}select,input[type=time]{font:inherit;color:inherit;background:var(--card-background-color,#fff);border:1px solid var(--divider-color,#ccc);border-radius:8px;padding:12px}button{font:inherit;cursor:pointer;color:var(--primary-color);background:transparent;border:1px solid var(--divider-color,#ddd);border-radius:8px;padding:10px 14px}button:disabled{opacity:.5;cursor:default}.remove{justify-self:end}.error{color:var(--error-color,#db4437);font-weight:bold}`;this.shadowRoot.append(style);
    const heading=document.createElement('h3');heading.textContent=this._label||t.title;this.shadowRoot.append(heading);
    const periods=[...this._value].sort((a,b)=>a.start.localeCompare(b.start));
    if(new Set(periods.map(p=>p.start)).size!==periods.length){const error=document.createElement('div');error.className='error';error.textContent=t.duplicate;this.shadowRoot.append(error);}
    for(let i=0;i<periods.length;i++){
      const p=periods[i],end=periods[(i+1)%periods.length].start,details=document.createElement('details');details.open=this.openIds.has(p.id);details.addEventListener('toggle',()=>{if(details.open)this.openIds.add(p.id);else this.openIds.delete(p.id);});
      const summary=document.createElement('summary');summary.textContent=periods.length===1?t.all:`${p.start}–${end}`;details.append(summary);const body=document.createElement('div');body.className='body';details.append(body);this.shadowRoot.append(details);
      if(periods.length>1){
      const timeRow=document.createElement('div');timeRow.className='row';const label=document.createElement('label');label.textContent=t.start;const time=document.createElement('input');time.type='time';time.step='60';time.value=p.start;time.disabled=!!this._disabled;label.append(time);const ending=document.createElement('span');ending.className='end';ending.textContent=periods.length===1?`— ${t.all}`:`— ${end}`;timeRow.append(label,ending);body.append(timeRow);
      time.addEventListener('change',()=>{if(time.value){p.start=time.value;this.emit();this.render();}});
      }
      const toggle=(name,value,change)=>{const row=document.createElement('label');row.className='row';const text=document.createElement('span');text.textContent=name;const control=document.createElement('ha-switch');control.checked=value;control.disabled=!!this._disabled;control.setAttribute('aria-label',name);control.addEventListener('change',()=>change(control.checked));row.append(text,control);body.append(row);};
      const select=(name,value,choices,change)=>{const label=document.createElement('label');label.className='field';label.append(document.createTextNode(name));const control=document.createElement('select');control.disabled=!!this._disabled;for(const [key,text] of choices){const o=document.createElement('option');o.value=key;o.textContent=text;control.append(o);}control.value=value;control.addEventListener('change',()=>change(control.value));label.append(control);body.append(label);};
      const field=(label,selector,value,change)=>{const control=document.createElement('ha-selector');control.hass=this._hass;control.label=label;control.selector=selector;control.value=value;control.disabled=!!this._disabled;control.required=true;control.addEventListener('value-changed',event=>{event.stopPropagation();control.value=event.detail.value;change(event.detail.value);});body.append(control);};
      toggle(t.quiet,!!p.do_not_disturb,value=>{p.do_not_disturb=value;this.emit();this.render();});
      if(p.do_not_disturb){const note=document.createElement('div');note.className='note';note.textContent=t.quietNote;body.append(note);}else{
        const st=p.startup||(p.startup={brightness:'unchanged',percentage:50,color:'unchanged',temperature:2700,rgb:[255,180,100]});
        select(t.brightness,st.brightness||'unchanged',[['unchanged',t.previous],['configured',t.configured]],value=>{st.brightness=value;this.emit();this.render();});
        const brightnessNote=document.createElement('div');brightnessNote.className='note';brightnessNote.textContent=t.help;body.append(brightnessNote);
        if(st.brightness==='configured')field(t.percent,{hrc_brightness:{}},st.percentage??50,value=>{st.percentage=value;this.emit();});
        select(t.color,st.color||'unchanged',[['unchanged',t.unchanged],['temperature',t.temperature],['rgb',t.rgb]],value=>{st.color=value;this.emit();this.render();});
        if(st.color==='temperature')field(t.temperature,{hrc_temperature:{}},st.temperature??2700,value=>{st.temperature=value;this.emit();});
        if(st.color==='rgb')field(t.rgb,{hrc_rgb:{}},st.rgb??[255,180,100],value=>{st.rgb=value;this.emit();});
        field(t.timeout,{hrc_timeout:{}},p.timeout??300,value=>{p.timeout=value;this.emit();});
        toggle(t.override,!!p.override_targets,value=>{p.override_targets=value;this.emit();this.render();});
        if(p.override_targets)field(t.targets,{entity:{domain:'light',multiple:true}},p.targets||[],value=>{p.targets=value;this.emit();});
      }
      if(periods.length>1){const remove=document.createElement('button');remove.type='button';remove.className='remove';remove.textContent=t.remove;remove.disabled=!!this._disabled;remove.addEventListener('click',()=>{this._value=this._value.filter(item=>item.id!==p.id);this.openIds.delete(p.id);if(this._value.length===1)this.openIds.add(this._value[0].id);this.emit();this.render();});body.append(remove);}
    }
    const add=document.createElement('button');add.type='button';add.textContent=`+ ${t.add}`;add.disabled=!!this._disabled;add.addEventListener('click',()=>this.add());this.shadowRoot.append(add);
  }
}
if(!customElements.get('ha-selector-hrc_motion_periods'))customElements.define('ha-selector-hrc_motion_periods',HrcMotionPeriods);

class HrcBrightnessSelector extends HrcLuxSelector {
  constructor(){
    super();this.slider.min='1';this.slider.max='100';this.slider.step='1';
    this.shadowRoot.querySelector('.reading').hidden=true;
    this.shadowRoot.querySelector('.warning').hidden=true;
    this.refresh();
  }
  reportValidity(){return Number.isInteger(this._value)&&this._value>=1&&this._value<=100;}
  refresh(){
    if(!this.slider)return;const value=this._value??50,text=`${value} %`;
    this.slider.value=String(value);this.slider.disabled=!!this._disabled;
    this.slider.setAttribute('aria-valuetext',text);
    this.shadowRoot.querySelector('label').textContent=this._label||'Brightness';
    this.shadowRoot.querySelector('output').textContent=text;
    const limits=this.shadowRoot.querySelectorAll('.limits span');
    limits[0].textContent='1 %';limits[1].textContent='100 %';
  }
}
if(!customElements.get('ha-selector-hrc_brightness'))customElements.define('ha-selector-hrc_brightness',HrcBrightnessSelector);

function hrcRgbToHs(rgb){
  const [r,g,b]=rgb.map(x=>x/255),max=Math.max(r,g,b),min=Math.min(r,g,b),delta=max-min;
  let hue=0;if(delta){hue=max===r?((g-b)/delta)%6:max===g?(b-r)/delta+2:(r-g)/delta+4;hue=(hue*60+360)%360;}
  return [Math.round(hue)%360,max===0?0:Math.round(delta/max*100)];
}
function hrcHsToRgb(hue,saturation){
  const s=saturation/100,c=s,x=c*(1-Math.abs((hue/60)%2-1)),m=1-c;
  const channels=hue<60?[c,x,0]:hue<120?[x,c,0]:hue<180?[0,c,x]:hue<240?[0,x,c]:hue<300?[x,0,c]:[c,0,x];
  return channels.map(v=>Math.round((v+m)*255));
}
class HrcRgbSelector extends HTMLElement {
  constructor(){
    super();this.attachShadow({mode:'open'});
    this.shadowRoot.innerHTML=`<style>
      :host{display:block;color:var(--primary-text-color);font:inherit}
      .heading{display:flex;align-items:center;gap:12px;margin-bottom:20px}.title{flex:1}.swatch{width:32px;height:32px;border-radius:50%;border:1px solid var(--divider-color,#ddd);box-shadow:0 0 0 3px var(--card-background-color,#fff)}.hex{font-size:13px;font-variant-numeric:tabular-nums;color:var(--secondary-text-color)}
      .field+.field{margin-top:20px}label{display:block;margin-bottom:12px}.row{display:flex;align-items:center;gap:16px;height:32px}input{flex:1;min-width:0;margin:0 2px;appearance:none;height:8px;border-radius:999px;cursor:pointer}input::-webkit-slider-thumb{appearance:none;width:18px;height:18px;border-radius:50%;border:2px solid white;background:var(--thumb);box-shadow:0 0 0 1px #0004}input::-moz-range-thumb{width:14px;height:14px;border-radius:50%;border:2px solid white;background:var(--thumb);box-shadow:0 0 0 1px #0004}input:focus-visible{outline:2px solid var(--primary-color);outline-offset:5px}input:disabled{opacity:.5;cursor:default}output{flex:0 0 76px;min-width:76px;text-align:right;white-space:nowrap;font-size:18px;font-variant-numeric:tabular-nums}
    </style><div class="heading"><span class="title"></span><span class="hex"></span><span class="swatch" role="img"></span></div><div class="field"><label for="hue"></label><div class="row"><input id="hue" type="range" min="0" max="359" step="1"><output for="hue"></output></div></div><div class="field"><label for="saturation"></label><div class="row"><input id="saturation" type="range" min="0" max="100" step="1"><output for="saturation"></output></div></div>`;
    this.hue=this.shadowRoot.querySelector('#hue');this.saturation=this.shadowRoot.querySelector('#saturation');
    for(const input of [this.hue,this.saturation]){
      input.addEventListener('input',()=>{
        this._hue=Number(this.hue.value);this._saturation=Number(this.saturation.value);
        this._value=hrcHsToRgb(this._hue,this._saturation);this.refresh();
        this.dispatchEvent(new CustomEvent('value-changed',{detail:{value:[...this._value]},bubbles:true,composed:true}));
      });input.addEventListener('change',event=>event.stopPropagation());
    }
    this.value=[255,180,100];
  }
  set hass(value){this._hass=value;this.refresh();}
  set selector(value){this._selector=value;}
  set label(value){this._label=value;this.refresh();}
  set disabled(value){this._disabled=value;this.refresh();}
  set required(value){this._required=value;}
  set value(value){
    if(!Array.isArray(value)||value.length!==3)return;
    if(JSON.stringify(value)!==JSON.stringify(this._value)){this._value=[...value];[this._hue,this._saturation]=hrcRgbToHs(value);}
    this.refresh();
  }
  get value(){return this._value;}
  focus(){this.hue.focus();}
  reportValidity(){return Array.isArray(this._value)&&this._value.length===3&&this._value.every(v=>Number.isInteger(v)&&v>=0&&v<=255);}
  refresh(){
    if(!this.hue||!this._value)return;
    const lang=this._hass?.language||'en',labels=lang.startsWith('cs')?['Vlastní barva','Odstín','Sytost']:lang.startsWith('sk')?['Vlastná farba','Odtieň','Sýtosť']:['Custom color','Hue','Saturation'];
    const hue=this._hue??0,saturation=this._saturation??0,hex='#'+this._value.map(v=>v.toString(16).padStart(2,'0')).join('').toUpperCase();
    this.shadowRoot.querySelector('.title').textContent=this._label||labels[0];
    this.shadowRoot.querySelector('.hex').textContent=hex;
    const swatch=this.shadowRoot.querySelector('.swatch');swatch.style.background=hex;swatch.setAttribute('aria-label',`${labels[0]} ${hex}`);
    this.hue.value=String(hue);this.saturation.value=String(saturation);
    this.hue.disabled=this.saturation.disabled=!!this._disabled;
    this.hue.style.background='linear-gradient(to right,#f00,#ff0,#0f0,#0ff,#00f,#f0f,#f00)';
    this.hue.style.setProperty('--thumb',`hsl(${hue} 100% 50%)`);
    this.saturation.style.background=`linear-gradient(to right,#fff,hsl(${hue} 100% 50%))`;
    this.saturation.style.setProperty('--thumb',hex);
    const caption=this.shadowRoot.querySelectorAll('.field label'),out=this.shadowRoot.querySelectorAll('output');
    caption[0].textContent=labels[1];caption[1].textContent=labels[2];out[0].textContent=`${hue}°`;out[1].textContent=`${saturation} %`;
    this.hue.setAttribute('aria-valuetext',`${hue}°`);this.saturation.setAttribute('aria-valuetext',`${saturation} %`);
  }
}
if(!customElements.get('ha-selector-hrc_rgb'))customElements.define('ha-selector-hrc_rgb',HrcRgbSelector);

// Scope native-picker cosmetics to this Motion form; retain HA's entity search.
function hrcOutlineMotionForm(element){
  let host=element,form;
  while(host){const root=host.getRootNode();host=root.host;if(host?.localName==='ha-form'){form=host;break;}}
  if(!form?.shadowRoot)return ()=>{};
  let frame=0,closed=false;const observers=new Map();
  const css=`
    ha-combo-box-item{background:var(--card-background-color,#fff)!important;border:1px solid var(--divider-color,#ccc);border-radius:8px!important;box-sizing:border-box}
    ha-combo-box-item::after{display:none!important}
    ha-combo-box-item:focus-within{border-color:var(--primary-color)}
    ha-combo-box-item:has(>span[slot="overline"]){--md-list-item-one-line-container-height:46px;--md-list-item-two-line-container-height:46px}
    span[slot="overline"]{position:absolute;width:1px;height:1px;overflow:hidden;clip-path:inset(50%)}
    .hrc-picker-label{margin-bottom:8px;font-size:14px;line-height:20px;color:var(--primary-text-color)}
  `;
  const enqueue=()=>{if(!closed&&!frame)frame=requestAnimationFrame(scan);};
  function scan(){
    frame=0;if(closed)return;
    for(const [root,observer] of observers){if(!root.host.isConnected){observer.disconnect();observers.delete(root);}}
    function walk(root){
      if(!observers.has(root)){const observer=new MutationObserver(enqueue);observer.observe(root,{childList:true,subtree:true});observers.set(root,observer);}
      for(const node of root.querySelectorAll('*')){
        if(node.localName==='ha-picker-field'&&node.shadowRoot&&!node.shadowRoot.querySelector('style[data-hrc-outlined]')){
          const style=document.createElement('style');style.dataset.hrcOutlined='';style.textContent=css;node.shadowRoot.append(style);
          const overline=node.shadowRoot.querySelector('span[slot="overline"]');
          if(overline){const label=document.createElement('div');label.className='hrc-picker-label';label.setAttribute('aria-hidden','true');label.textContent=overline.textContent.replace(/\s*\*\s*$/,'');node.shadowRoot.prepend(label);}
        }
        if(node.shadowRoot)walk(node.shadowRoot);
      }
    }
    walk(form.shadowRoot);
  }
  enqueue();
  return ()=>{closed=true;if(frame)cancelAnimationFrame(frame);for(const observer of observers.values())observer.disconnect();observers.clear();};
}

class HrcBridgeSettings extends HTMLElement {
  constructor(){super();this.attachShadow({mode:'open'});this._value={};this.open=true;}
  connectedCallback(){this._stopStyling=hrcOutlineMotionForm(this);}
  disconnectedCallback(){this._stopStyling?.();}
  set hass(value){const lang=this._hass?.language;this._hass=value;if(lang!==value?.language)this.render();else for(const c of this.shadowRoot.querySelectorAll('ha-selector'))c.hass=value;}
  set value(value){if(JSON.stringify(value)===JSON.stringify(this._value))return;this._value=structuredClone(value||{});this.render();}
  get value(){return this._value;}
  set selector(value){}
  set label(value){}
  set required(value){}
  set disabled(value){if(this._disabled===!!value)return;this._disabled=!!value;this.render();}
  emit(){this.dispatchEvent(new CustomEvent('value-changed',{detail:{value:structuredClone(this._value)},bubbles:true,composed:true}));}
  text(){const lang=this._hass?.language||'en';return lang.startsWith('cs')?{
    enable:'Blokovat chování entitou',block:'Blokovaná ovládání',motion:'Blokovat Motion',button:'Blokovat Button',dial:'Blokovat Dial',dimmer:'Blokovat Dimmer',entity:'Řídicí entita',states:'Povolené stavy',help:'Zadejte přesné stavy, při kterých je ovládání povoleno. Více hodnot oddělte čárkou. Jiný, neznámý nebo nedostupný stav zablokuje vybraná ovládání. Běžící cykly Motionu mohou doběhnout.',mode:'Režim pollingu',active:'Po první události',continuous:'Trvale',interval:'Interval čtení (sekundy)',window:'Doba čtení po pohybu (sekundy)',pollingNote:'Trvalý polling dotazuje Hue Bridge i v klidu. Kratší interval znamená více požadavků, vyšší síťový provoz a větší výpočetní zátěž Home Assistantu i Bridge. Režim „Po první události“ spouští polling dočasně a je úspornější. Požadavky jsou hromadné a sdílené mezi ovladači.'
  }:lang.startsWith('sk')?{
    enable:'Blokovať správanie entitou',block:'Blokované ovládania',motion:'Blokovať Motion',button:'Blokovať Button',dial:'Blokovať Dial',dimmer:'Blokovať Dimmer',entity:'Riadiaca entita',states:'Povolené stavy',help:'Zadajte presné stavy, pri ktorých je ovládanie povolené. Viaceré hodnoty oddeľte čiarkou. Iný, neznámy alebo nedostupný stav zablokuje vybrané ovládania. Prebiehajúce cykly Motionu môžu dobehnúť.',mode:'Režim pollingu',active:'Po prvej udalosti',continuous:'Trvalo',interval:'Interval čítania (sekundy)',window:'Doba čítania po pohybe (sekundy)',pollingNote:'Trvalý polling sa dopytuje Hue Bridge aj v pokoji. Kratší interval znamená viac požiadaviek, vyššiu sieťovú prevádzku a väčšiu výpočtovú záťaž Home Assistantu aj Bridge. Režim „Po prvej udalosti“ spúšťa polling dočasne a je úspornejší. Požiadavky sú hromadné a zdieľané medzi ovládačmi.'
  }:{enable:'Block control by entity',block:'Blocked controllers',motion:'Block Motion',button:'Block Button',dial:'Block Dial',dimmer:'Block Dimmer',entity:'Control entity',states:'Allowed states',help:'Enter the exact states that allow control, separated by commas. Other, unknown or unavailable states block the selected controllers. Running Motion cycles can finish.',mode:'Polling mode',active:'After first event',continuous:'Continuous',interval:'Read interval (seconds)',window:'Active window after movement (seconds)',pollingNote:'Continuous polling queries Hue Bridge even while idle. Shorter intervals increase request volume, network traffic and processing load on Home Assistant and the bridge. “After first event” starts polling temporarily and uses fewer resources. Requests are batched and shared across controllers.'};}
  reportValidity(){return !this._value.motion_gate_enabled||Boolean(this._value.motion_gate_entity&&this._value.motion_gate_states?.trim());}
  render(){
    if(!this.shadowRoot)return;const t=this.text(),v=this._value;
    this.shadowRoot.innerHTML=`<style>:host{display:block;color:var(--primary-text-color);font:inherit}.row{display:flex;align-items:center;justify-content:space-between;gap:16px;padding:12px 0}.field{display:flex;flex-direction:column;gap:8px;margin:16px 0}select,input{font:inherit;color:inherit;background:var(--card-background-color,#fff);border:1px solid var(--divider-color,#ccc);border-radius:8px;padding:12px;box-sizing:border-box;width:100%}details{border:1px solid var(--divider-color,#ccc);border-radius:12px;padding:16px;margin:8px 0 24px}summary{cursor:pointer;font-weight:600}.note{color:var(--secondary-text-color);font-size:13px;line-height:1.5;margin:8px 0}ha-selector{display:block;margin:16px 0}</style>`;
    const toggle=(parent,name,key,fallback=false)=>{
      // A native label can forward a second click into ha-switch's own input.
      // Keep the switch mounted during family changes so its animation/focus survives.
      const row=document.createElement('div');row.className='row';const text=document.createElement('span');text.textContent=name;
      const sw=document.createElement('ha-switch');sw.setAttribute('aria-label',name);sw.checked=v[key]??fallback;sw.disabled=!!this._disabled;
      text.addEventListener('click',()=>{if(!sw.disabled)sw.click();});
      sw.addEventListener('change',event=>{event.stopPropagation();this._value[key]=sw.checked;this.emit();if(key==='motion_gate_enabled')this.render();});
      row.append(text,sw);parent.append(row);
    };
    const field=(parent,name,key,type='text',extra={})=>{const label=document.createElement('label');label.className='field';label.append(document.createTextNode(name));const input=document.createElement('input');input.type=type;input.value=type==='number'&&Number.isFinite(v[key])?Number(v[key].toFixed(2)):(v[key]??'');Object.assign(input,extra);input.disabled=!!this._disabled;input.addEventListener('input',()=>{v[key]=type==='number'?Number(input.value):input.value;this.emit();});label.append(input);parent.append(label);};
    toggle(this.shadowRoot,t.enable,'motion_gate_enabled');
    if(v.motion_gate_enabled){
      const details=document.createElement('details');details.open=this.open;details.addEventListener('toggle',()=>{this.open=details.open;});const summary=document.createElement('summary');summary.textContent=t.block;details.append(summary);this.shadowRoot.append(details);
      for(const k of ['motion','button','dial','dimmer'])toggle(details,t[k],'gate_'+k,k==='motion');
      const entity=document.createElement('ha-selector');entity.hass=this._hass;entity.label=t.entity;entity.selector={entity:{}};entity.value=v.motion_gate_entity||undefined;entity.disabled=!!this._disabled;entity.addEventListener('value-changed',event=>{event.stopPropagation();entity.value=event.detail.value;v.motion_gate_entity=event.detail.value||'';this.emit();});details.append(entity);
      field(details,t.states,'motion_gate_states');const note=document.createElement('div');note.className='note';note.textContent=t.help;details.append(note);
    }
    const label=document.createElement('label');label.className='field';label.append(document.createTextNode(t.mode));const select=document.createElement('select');select.disabled=!!this._disabled;for(const [key,text] of [['active',t.active],['continuous',t.continuous]]){const option=document.createElement('option');option.value=key;option.textContent=text;select.append(option);}select.value=v.polling_mode||'active';select.addEventListener('change',()=>{v.polling_mode=select.value;this.emit();this.render();});label.append(select);this.shadowRoot.append(label);
    if(v.polling_mode==='continuous'){field(this.shadowRoot,t.interval,'poll_interval','number',{min:0.1,max:2,step:0.05});field(this.shadowRoot,t.window,'active_window','number',{min:1,max:10,step:0.5});}
    const note=document.createElement('div');note.className='note';note.textContent=t.pollingNote;this.shadowRoot.append(note);
  }
}
if(!customElements.get('ha-selector-hrc_bridge_settings'))customElements.define('ha-selector-hrc_bridge_settings',HrcBridgeSettings);

// Reuse the Motion form's switches, outlined pickers and slider geometry.
class HrcControlEnabled extends HrcMotionEnabled {
  connectedCallback(){this._stopStyling=hrcOutlineMotionForm(this);}
  disconnectedCallback(){this._stopStyling?.();}
}
if(!customElements.get('ha-selector-hrc_control_enabled'))customElements.define('ha-selector-hrc_control_enabled',HrcControlEnabled);

class HrcNumberSelector extends HrcLuxSelector {
  reportValidity(){const c=this._selector?.hrc_number||{};return Number.isFinite(this._value)&&this._value>=c.min&&this._value<=c.max;}
  refresh(){
    if(!this.slider)return;
    const c=this._selector?.hrc_number||{min:0.1,max:10,step:0.05};
    this.slider.min=String(c.min);this.slider.max=String(c.max);this.slider.step=String(c.step||1);
    const value=this._value??c.min,format=new Intl.NumberFormat(this._hass?.language||'en',{maximumFractionDigits:2});
    const text=format.format(value)+(c.unit_of_measurement?' '+c.unit_of_measurement:'');
    this.slider.value=String(value);this.slider.disabled=!!this._disabled;this.slider.setAttribute('aria-valuetext',text);
    this.shadowRoot.querySelector('label').textContent=this._label||'';this.shadowRoot.querySelector('output').textContent=text;
    const limits=this.shadowRoot.querySelectorAll('.limits span');limits[0].textContent=format.format(c.min);limits[1].textContent=format.format(c.max);
    this.shadowRoot.querySelector('.reading').hidden=true;this.shadowRoot.querySelector('.warning').hidden=true;
  }
}
if(!customElements.get('ha-selector-hrc_number'))customElements.define('ha-selector-hrc_number',HrcNumberSelector);

class HrcHeading extends HTMLElement {
  constructor(){super();this.attachShadow({mode:'open'});this.shadowRoot.innerHTML='<style>:host{display:block;margin:12px 0 0;color:var(--primary-text-color);font-weight:600}h3{font:inherit;margin:0}</style><h3></h3>';}
  set label(value){this.shadowRoot.querySelector('h3').textContent=value||'';}
  set value(value){this._value=value;}
  get value(){return this._value;}
  set hass(value){}
  set selector(value){}
  set disabled(value){}
  reportValidity(){return true;}
}
if(!customElements.get('ha-selector-hrc_heading'))customElements.define('ha-selector-hrc_heading',HrcHeading);

// Shared switch-on appearance for all controller button gestures.
class HrcButtonAction extends HTMLElement {
  constructor(){super();this.attachShadow({mode:'open'});this._value={};}
  connectedCallback(){
    this.forms=[];let host=this;
    while(host){if(host.localName==='ha-form')this.forms.push(host);host=host.parentElement||host.getRootNode()?.host;}
    this.contextChanged=event=>{if(event.composedPath().includes(this))return;cancelAnimationFrame(this.frame);this.frame=requestAnimationFrame(()=>{const type=this.targetType();if(type!==this.type)this.render();});};
    for(const form of this.forms)form.addEventListener('value-changed',this.contextChanged);
    this.render();
  }
  disconnectedCallback(){cancelAnimationFrame(this.frame);for(const f of this.forms||[])f.removeEventListener('value-changed',this.contextChanged);}
  set hass(v){const language=this._hass?.language;this._hass=v;if(language!==v?.language)this.render();else for(const c of this.shadowRoot.querySelectorAll('ha-selector'))c.hass=v;}
  set selector(v){if(JSON.stringify(v)===JSON.stringify(this._selector))return;this._selector=v;this.render();}
  set value(v){if(JSON.stringify(v)===JSON.stringify(this._value))return;this._value=structuredClone(v||{});this.render();}
  get value(){return this._value;}
  set label(v){}
  set required(v){}
  set disabled(v){if(this._disabled===!!v)return;this._disabled=!!v;this.render();}
  targetType(){
    const config=this._selector?.hrc_button_action||{},action=config.action;
    const section=this.forms?.find(f=>f.data&&Object.hasOwn(f.data,action+'_enabled'))?.data;
    const outer=this.forms?.find(f=>f.data&&Object.hasOwn(f.data,'shared_targets'))?.data;
    let selected=section?.[action+'_targets']??config.targets??[];
    if(config.kind!=='tap_dial'&&section?.[action+'_other_targets']!==true)selected=outer?.shared_targets??config.shared??[];
    return selected.length&&selected.every(e=>e.startsWith('light.'))?'light':selected.length&&selected.every(e=>e.startsWith('fan.')||e.startsWith('number.'))?'percentage':'other';
  }
  emit(){this.dispatchEvent(new CustomEvent('value-changed',{detail:{value:structuredClone(this._value)},bubbles:true,composed:true}));}
  render(){
    if(!this.shadowRoot)return;this.type=this.targetType();const type=this.type,c=this._selector?.hrc_button_action||{},v=this._value;
    const motionText=HrcMotionPeriods.prototype.text.call(this),lang=this._hass?.language||'en';
    const local=lang.startsWith('cs')?{action:'Akce',power:'Zapnutí / vypnutí',on:'Pouze zapnout',off:'Pouze vypnout',previous:'Předchozí stav obnoví uložený jas; po dohasnutí Motionu použije jas před ztlumením. Bez uložené hodnoty se jas neposílá. Barva se nastavuje samostatně.'}:lang.startsWith('sk')?{action:'Akcia',power:'Zapnutie / vypnutie',on:'Iba zapnúť',off:'Iba vypnúť',previous:'Predchádzajúci stav obnoví uložený jas; po dohasnutí Motionu použije jas pred stlmením. Bez uloženej hodnoty sa jas neposiela. Farba sa nastavuje samostatne.'}:{action:'Action',power:'Turn on / off',on:'Turn on only',off:'Turn off only',previous:'Previous state restores saved brightness; after Motion fades, it uses the pre-fade level. Without a saved level no brightness is sent. Color is configured separately.'};
    const labels=this._hass?.localize?key=>this._hass.localize('component.hue_reconfigo.selector.button_operation.options.'+key)||key:key=>key;
    this.shadowRoot.innerHTML=`<style>:host{display:grid;gap:16px;color:var(--primary-text-color);font:inherit}.field{display:grid;gap:8px;font-size:14px}select{font:inherit;color:inherit;background:var(--card-background-color,#fff);border:1px solid var(--divider-color,#ccc);border-radius:8px;padding:12px;width:100%;box-sizing:border-box}.note{color:var(--secondary-text-color);font-size:13px;line-height:1.5}</style>`;
    const choose=(name,value,choices,change)=>{const label=document.createElement('label');label.className='field';label.append(document.createTextNode(name));const select=document.createElement('select');select.disabled=this._disabled;for(const [key,text] of choices){const o=document.createElement('option');o.value=key;o.textContent=text;select.append(o);}select.value=value;select.addEventListener('change',()=>{change(select.value);this.emit();this.render();});label.append(select);this.shadowRoot.append(label);};
    const field=(name,selector,value,change)=>{const control=document.createElement('ha-selector');control.hass=this._hass;control.label=name;control.selector=selector;control.value=value;control.required=true;control.disabled=this._disabled;control.addEventListener('value-changed',e=>{e.stopPropagation();control.value=e.detail.value;change(e.detail.value);this.emit();});this.shadowRoot.append(control);};
    const power=['toggle','previous','configured','on'].includes(v.operation||'toggle');
    const options=type==='light'?[['toggle',local.power]]:type==='percentage'?['toggle','previous','configured'].map(k=>[k,labels(k)]):[['toggle',local.power]];
    options.push(['on',local.on],['off',local.off]);
    if(c.action==='short'&&c.kind==='dimmer'&&[2,3].includes(c.index))options.push(['step_up',labels('step_up')],['step_down',labels('step_down')]);
    if(c.action==='long')options.push(['dimming',labels('dimming')]);
    if(c.kind==='tap_dial'&&c.index>1)options.push(['dial',labels('dial')]);
    if(options.length>1)choose(local.action,type==='light'&&['previous','configured'].includes(v.operation)?'toggle':v.operation||'toggle',options,value=>{v.operation=value;});
    if(type==='percentage'&&['configured','on'].includes(v.operation))field(motionText.percent,{hrc_brightness:{}},v.percentage??100,value=>{v.percentage=value;});
    if(type!=='light'||!power)return;
    const st=v.startup||(v.startup={brightness:v.operation==='configured'?'configured':'unchanged',percentage:v.percentage??100,color:'unchanged',temperature:2700,rgb:[255,180,100]});
    choose(motionText.brightness,st.brightness||'unchanged',[['unchanged',motionText.previous],['configured',motionText.configured]],value=>{st.brightness=value;if(v.operation!=='on')v.operation='toggle';});
    if(st.brightness==='configured')field(motionText.percent,{hrc_brightness:{}},st.percentage??50,value=>{st.percentage=value;});
    else {const note=document.createElement('div');note.className='note';note.textContent=local.previous;this.shadowRoot.append(note);}
    choose(motionText.color,st.color||'unchanged',[['unchanged',motionText.unchanged],['temperature',motionText.temperature],['rgb',motionText.rgb]],value=>{st.color=value;if(v.operation!=='on')v.operation='toggle';});
    if(st.color==='temperature')field(motionText.temperature,{hrc_temperature:{}},st.temperature??2700,value=>{st.temperature=value;});
    if(st.color==='rgb')field(motionText.rgb,{hrc_rgb:{}},st.rgb??[255,180,100],value=>{st.rgb=value;});
  }
}
if(!customElements.get('ha-selector-hrc_button_action'))customElements.define('ha-selector-hrc_button_action',HrcButtonAction);

class HrcMotionBehavior extends HTMLElement {
 constructor(){super();this.attachShadow({mode:'open'});this._value={};this.open=false;}
 set value(v){
  const next=structuredClone(v||{});
  if(next.manual_change==='handover'&&next.manual_scope==='all')next.manual_change='handover_all';
  next.return='off';next.return_seconds=300;
  if(JSON.stringify(next)===JSON.stringify(this._value))return;
  this._value=next;this.render();
 }
 get value(){return this._value;}
 set hass(v){const lang=this._hass?.language;this._hass=v;if(lang!==v?.language)this.render();}
 set selector(v){}
 set label(v){}
 set required(v){}
 set disabled(v){if(this._disabled===!!v)return;this._disabled=!!v;this.render();}
 emit(){
  this._value.manual_scope=this._value.manual_change==='handover_all'?'all':'touched';
  this.dispatchEvent(new CustomEvent('value-changed',{detail:{value:structuredClone(this._value)},bubbles:true,composed:true}));
 }
 text(){const l=this._hass?.language||'en';return l.startsWith('cs')?{
 title:'Jak Motion spolupracuje s ostatním ovládáním',arrivalTitle:'Světla, která už svítí při příchodu',arrival:'Při prvním pohybu',apply:'Použít nastavený jas a barvu ze sekce „Vyhrazené časy“',keep:'Ponechat aktuální jas a barvu',departure:'Po uplynutí času bez pohybu',off:'Zhasnout také tato světla',stay:'Nechat je svítit',restore:'Vrátit jas a barvu z okamžiku příchodu',arrivalNote:'Tato nastavení platí pro světla, která svítila už před zahájením řízení Motionem.',manualTitle:'Zásah ovladačem',change:'Po ruční změně jasu nebo barvy v průběhu cyklu má Motion automaticky zhasnout?',all:'Ano, všechna světla',none:'Ne, žádná světla',untouched:'Jen světla, která nebyla ručně ovládaná',manualOff:'Když ovladačem zhasnu',resume:'Další pohyb smí znovu hned rozsvítit',hold:'Ponechat zhasnuté do skončení aktuálního cyklu',note:'Platí pouze pro ovladače nastavené v Hue Reconfigo. Změny z aplikací ani jiných automatizací se za zásah ovladačem nepovažují.',returnNote:'Motion obnoví plné automatické ovládání těchto světel až po jejich vypnutí, dokončení aktuálního cyklu a nové detekci pohybu.'
 }:l.startsWith('sk')?{
 title:'Ako Motion spolupracuje s ostatným ovládaním',arrivalTitle:'Svetlá, ktoré už svietia pri príchode',arrival:'Pri prvom pohybe',apply:'Použiť nastavený jas a farbu zo sekcie „Vyhradené časy“',keep:'Ponechať aktuálny jas a farbu',departure:'Po uplynutí času bez pohybu',off:'Zhasnúť aj tieto svetlá',stay:'Nechať ich svietiť',restore:'Vrátiť jas a farbu z okamihu príchodu',arrivalNote:'Tieto nastavenia platia pre svetlá, ktoré svietili už pred začatím riadenia Motionom.',manualTitle:'Zásah ovládačom',change:'Má Motion po ručnej zmene jasu alebo farby počas cyklu automaticky zhasnúť?',all:'Áno, všetky svetlá',none:'Nie, žiadne svetlá',untouched:'Iba svetlá, ktoré neboli ručne ovládané',manualOff:'Keď ovládačom zhasnem',resume:'Ďalší pohyb smie znovu hneď rozsvietiť',hold:'Ponechať zhasnuté do skončenia aktuálneho cyklu',note:'Platí iba pre ovládače nastavené v Hue Reconfigo. Zmeny z aplikácií ani iných automatizácií sa nepovažujú za zásah ovládačom.',returnNote:'Motion obnoví plné automatické ovládanie týchto svetiel až po ich vypnutí, dokončení aktuálneho cyklu a novej detekcii pohybu.'
 }:{title:'How Motion works with other controls',arrivalTitle:'Lights already on when you arrive',arrival:'On the first motion detection',apply:'Apply brightness and color from Dedicated times',keep:'Keep current brightness and color',departure:'After the no-motion timeout',off:'Turn these lights off too',stay:'Leave them on',restore:'Restore brightness and color from arrival',arrivalNote:'These settings apply to lights that were already on before Motion started its cycle.',manualTitle:'Controller intervention',change:'After a manual brightness or color change during the cycle, should Motion turn lights off automatically?',all:'Yes, all lights',none:'No, none of the lights',untouched:'Only lights that were not manually controlled',manualOff:'When I turn lights off with a controller',resume:'The next motion detection may turn them on again immediately',hold:'Keep them off until the current cycle ends',note:'Only controllers configured in Hue Reconfigo count as manual intervention. Changes from apps or other automations do not.',returnNote:'Motion resumes full automatic control of these lights only after they have been turned off, the current cycle has finished, and motion is detected again.'};}
 render(){
  if(!this.shadowRoot)return;const t=this.text(),v=this._value;
  this.shadowRoot.innerHTML='<style>:host{display:block;color:var(--primary-text-color);font:inherit}details{border:1px solid var(--divider-color,#ccc);border-radius:12px}summary{padding:16px;cursor:pointer;font-weight:500}.body{padding:0 16px 16px;display:grid;gap:16px}h3{font-size:15px;margin:12px 0 0}.field{display:grid;gap:8px;font-size:14px}select{font:inherit;color:inherit;background:var(--card-background-color,#fff);border:1px solid var(--divider-color,#ccc);border-radius:8px;padding:12px;width:100%;box-sizing:border-box}.note{font-size:13px;color:var(--secondary-text-color);line-height:1.5}</style>';
  const details=document.createElement('details');details.open=this.open;details.addEventListener('toggle',()=>{this.open=details.open;});const summary=document.createElement('summary');summary.textContent=t.title;details.append(summary);const body=document.createElement('div');body.className='body';details.append(body);this.shadowRoot.append(details);
  const text=(tag,value,cls)=>{const e=document.createElement(tag);e.textContent=value;if(cls)e.className=cls;body.append(e);return e;};
  const select=(name,key,fallback,choices)=>{const label=text('label','','field');label.append(document.createTextNode(name));const control=document.createElement('select');control.disabled=this._disabled;for(const [value,caption] of choices){const option=document.createElement('option');option.value=value;option.textContent=caption;control.append(option);}control.value=v[key]||fallback;control.addEventListener('change',()=>{v[key]=control.value;this.emit();this.render();});label.append(control);};
  text('h3',t.arrivalTitle);select(t.arrival,'arrival','apply',[['apply',t.apply],['keep',t.keep]]);select(t.departure,'departure','off',[['off',t.off],['keep',t.stay],['restore',t.restore]]);text('div',t.arrivalNote,'note');
  text('h3',t.manualTitle);text('div',t.note,'note');select(t.change,'manual_change','continue',[['continue',t.all],['handover_all',t.none],['handover',t.untouched]]);
  if(['handover','handover_all'].includes(v.manual_change))text('div',t.returnNote,'note');
  select(t.manualOff,'manual_off','hold',[['resume',t.resume],['hold',t.hold]]);
 }
}
if(!customElements.get('ha-selector-hrc_motion_behavior'))customElements.define('ha-selector-hrc_motion_behavior',HrcMotionBehavior);
