import {request,post,patch} from './client';import {parseMarks} from '../utils/constraints';
const send=(id:number,body:any)=>patch('/traces/'+id,body);
export const catalogApi={
 studies:()=>request('/studies'),traces:()=>request('/traces'),profiles:()=>request('/profiles'),
 createStudy:(data:any)=>post('/studies',data),createProfile:(data:any)=>post('/profiles',data),
 // tokens and marks are edited independently; passing undefined leaves the other field untouched server-side.
 editTrace:(id:number,tokens:string[]|undefined,marksText:string|undefined,tokenCount:number,stateCount:number)=>{
  const body:any={};
  if(tokens!==undefined)body.tokens=tokens;
  if(marksText!==undefined)body.constraints=parseMarks(marksText,tokenCount,stateCount);
  return send(id,body);
 }};
