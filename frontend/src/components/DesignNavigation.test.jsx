import React from 'react';
import { vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import Navigation from './Navigation';
import LandingPage from './LandingPage';
import { useAuth } from '../hooks/useAuth';
vi.mock('../hooks/useAuth', () => ({ useAuth: vi.fn() }));
// Preload the real lazy module so role/navigation assertions do not depend
// on parallel transform time; keep the actual component and lazy boundary.
beforeAll(async () => { await import('./WorkspaceNavigation'); });
beforeEach(() => useAuth.mockReturnValue({ isAuthenticated:false, userInfo:null, logout:vi.fn() }));
test('workflow tabs support keyboard navigation, focus and matching content', () => {
 render(<MemoryRouter><LandingPage /></MemoryRouter>);
 const tabs = screen.getAllByRole('tab');
 expect(tabs[0]).toHaveAttribute('aria-selected','true');
 fireEvent.keyDown(tabs[0],{key:'ArrowRight'});
 expect(tabs[1]).toHaveFocus();
 expect(tabs[1]).toHaveAttribute('aria-selected','true');
 expect(screen.getByRole('tabpanel')).toHaveTextContent('從分散的紀錄，到清楚的輪廓。');
 for (const modifier of ['ctrlKey', 'altKey', 'metaKey']) {
  expect(fireEvent.keyDown(tabs[1], { key: 'Home', [modifier]: true })).toBe(true);
  expect(tabs[1]).toHaveFocus();
  expect(tabs[1]).toHaveAttribute('aria-selected', 'true');
 }
 fireEvent.keyDown(tabs[1],{key:'End'});
 expect(tabs[2]).toHaveFocus();
 expect(screen.getByRole('link',{name:/探索研究工作台/})).toHaveAttribute('href','/research-cohorts');
 fireEvent.keyDown(tabs[2],{key:'ArrowRight'});
 expect(tabs[0]).toHaveFocus();
});
test('public navigation exposes actual sign in and account application links', () => {
 render(<MemoryRouter><Navigation /></MemoryRouter>);
 expect(screen.getByRole('link',{name:'登入'})).toHaveAttribute('href','/login');
 expect(screen.getByRole('link',{name:/申請帳號/})).toHaveAttribute('href','/register');
});
test('patient role does not see research navigation and a nested chart keeps patients active', async () => {
 useAuth.mockReturnValue({isAuthenticated:true,userInfo:{username:'Test user',role:'patient'},logout:vi.fn()});
 render(<MemoryRouter initialEntries={['/patients/42']}><Navigation /></MemoryRouter>);
 expect(await screen.findByRole('link',{name:'病患'})).toHaveAttribute('aria-current','page');
 expect(screen.queryByRole('link',{name:'研究 Cohort'})).not.toBeInTheDocument();
 expect(screen.getByRole('button',{name:'帳號選單'})).toHaveAttribute('aria-expanded','false');
});
test('researcher can reach research workflows', async () => {
 useAuth.mockReturnValue({isAuthenticated:true,userInfo:{username:'Test researcher',role:'researcher'},logout:vi.fn()});
 render(<MemoryRouter><Navigation /></MemoryRouter>);
 expect(await screen.findByRole('link',{name:'研究 Cohort'})).toHaveAttribute('href','/research-cohorts');
 expect(screen.getByRole('link',{name:'研究報告'})).toHaveAttribute('href','/research-reports');
});

test('session verification presents a status before exposing account routes',()=>{
 useAuth.mockReturnValue({loading:true,isAuthenticated:false,userInfo:null,logout:vi.fn()});render(<MemoryRouter><Navigation/></MemoryRouter>);expect(screen.getByRole('status')).toHaveTextContent('正在確認工作空間');expect(screen.queryByRole('link',{name:'登入'})).not.toBeInTheDocument();
});
test('ending a session removes the workspace menu and returns public navigation',async()=>{
 useAuth.mockReturnValue({loading:false,isAuthenticated:true,userInfo:{username:'Synthetic clinician',role:'clinician'},logout:vi.fn()});const view=render(<MemoryRouter><Navigation/></MemoryRouter>);fireEvent.click(await screen.findByRole('button',{name:'帳號選單'}));expect(await screen.findByRole('menuitem',{name:'登出'})).toBeInTheDocument();useAuth.mockReturnValue({loading:false,isAuthenticated:false,userInfo:null,logout:vi.fn()});view.rerender(<MemoryRouter><Navigation/></MemoryRouter>);expect(screen.getByRole('link',{name:'登入'})).toHaveAttribute('href','/login');expect(screen.queryByRole('menuitem',{name:'登出'})).not.toBeInTheDocument();expect(screen.queryByRole('button',{name:'帳號選單'})).not.toBeInTheDocument();
});

test('Viewer navigation excludes writes and research', async () => {
 useAuth.mockReturnValue({isAuthenticated:true,userInfo:{username:'Synthetic Viewer',role:'viewer'},logout:vi.fn()});
 render(<MemoryRouter><Navigation/></MemoryRouter>);
 await screen.findByRole('link',{name:'病患'});
 expect(screen.queryByRole('link',{name:'健檢輸入'})).not.toBeInTheDocument();
 expect(screen.queryByRole('link',{name:'資料匯入'})).not.toBeInTheDocument();
 expect(screen.queryByRole('link',{name:'研究 Cohort'})).not.toBeInTheDocument();
});


test.each([false,true])('home primary actions follow authenticated state %s',isAuthenticated=>{
 useAuth.mockReturnValue({isAuthenticated,userInfo:isAuthenticated?{role:'viewer'}:null});
 render(<MemoryRouter><LandingPage/></MemoryRouter>);
 if(isAuthenticated){
  const actions=screen.getAllByRole('link',{name:'返回工作空間'});
  expect(actions).toHaveLength(2);
  actions.forEach(action=>expect(action).toHaveAttribute('href','/dashboard'));
  expect(screen.queryByRole('link',{name:'登入工作空間'})).not.toBeInTheDocument();
 }else{
  expect(screen.getByRole('link',{name:'登入工作空間'})).toHaveAttribute('href','/login');
  expect(screen.getByRole('link',{name:'申請帳號'})).toHaveAttribute('href','/register');
 }
});


test.each([['viewer',['臨床照護']],['researcher',['臨床照護','研究探索']],['manager',['臨床照護','資料整合','研究探索']]])('authenticated %s home exposes permitted workflows', (role,labels)=>{
 useAuth.mockReturnValue({isAuthenticated:true,userInfo:{role}});
 render(<MemoryRouter><LandingPage/></MemoryRouter>);
 const tabs=screen.getAllByRole('tab');
 expect(tabs).toHaveLength(labels.length);
 labels.forEach((label,index)=>expect(tabs[index]).toHaveTextContent(label));
 fireEvent.keyDown(tabs[0],{key:'End'});
 expect(tabs[tabs.length-1]).toHaveFocus();
 expect(tabs[tabs.length-1]).toHaveAttribute('aria-selected','true');
 fireEvent.keyDown(tabs[tabs.length-1],{key:'ArrowRight'});
 expect(tabs[0]).toHaveFocus();
});


test('home selected workflow remains valid when authenticated permissions change',()=>{
 useAuth.mockReturnValue({isAuthenticated:true,userInfo:{role:'manager'}});
 const view=render(<MemoryRouter><LandingPage/></MemoryRouter>);
 fireEvent.click(screen.getByRole('tab',{name:/研究探索/}));
 expect(screen.getByRole('link',{name:/探索研究工作台/})).toHaveAttribute('href','/research-cohorts');
 useAuth.mockReturnValue({isAuthenticated:true,userInfo:{role:'viewer'}});
 view.rerender(<MemoryRouter><LandingPage/></MemoryRouter>);
 const tab=screen.getByRole('tab');
 expect(tab).toHaveAttribute('aria-selected','true');
 expect(tab).toHaveTextContent('臨床照護');
 expect(screen.getByRole('tabpanel')).toHaveAttribute('aria-labelledby',tab.id);
 expect(screen.queryByRole('link',{name:/探索研究工作台/})).not.toBeInTheDocument();
 expect(screen.getByRole('link',{name:/進入臨床工作台/})).toHaveAttribute('href','/patients');
 fireEvent.keyDown(tab,{key:'ArrowLeft'});
 expect(tab).toHaveFocus();
});
