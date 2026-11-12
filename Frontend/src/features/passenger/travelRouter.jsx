import React from 'react'
import {Link as RouterLink,Navigate as RouterNavigate,useNavigate as useRouterNavigate} from 'react-router-dom'
import {useWorkspace} from '../../context/workspaceContext'
import {travelPath} from '../../routes/workspaceRoutes'

/* The Passenger pages are shared. Inside the Owner or Driver workspace (contract 03W) they run under <prefix>/travel/...,
   so these drop-in versions of Link / Navigate / useNavigate rewrite a Passenger path to the current workspace.
   Passenger and signed-out pages are untouched. */
export function useTravelPath(){const workspace=useWorkspace(),role=workspace?.role;return React.useCallback(path=>travelPath(role,path),[role])}
export function useNavigate(){const go=useRouterNavigate(),to=useTravelPath();return React.useCallback((target,options)=>typeof target==='string'?go(to(target),options):go(target,options),[go,to])}
export const Link=React.forwardRef(function TravelLink({to,...rest},ref){const path=useTravelPath();return <RouterLink ref={ref} to={typeof to==='string'?path(to):to} {...rest}/>})
export function Navigate({to,...rest}){const path=useTravelPath();return <RouterNavigate to={typeof to==='string'?path(to):to} {...rest}/>}
