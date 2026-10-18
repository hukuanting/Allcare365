import React, { lazy } from 'react';
import { vi } from 'vitest';
import { act, fireEvent, render, screen } from '@testing-library/react';
import { Link, MemoryRouter, Route, Routes, useNavigate } from 'react-router-dom';
import RouteExperience, { PageNotFound, routeTitle } from './RouteExperience';
import ProtectedRoute from './ProtectedRoute';
const auth=vi.hoisted(()=>({state:{isAuthenticated:true,userInfo:{role:'patient'}}}));
vi.mock('../utils/auth',()=>({checkAuthStatus:()=>auth.state}));
function Controls(){const navigate=useNavigate();return <nav><Link to="/patients/73">Open chart</Link><Link to="/broken">Open broken</Link><Link to="/slow">Open slow</Link><button onClick={()=>navigate('?search=new')}>Update query</button></nav>;}
function Failure(){throw new Error('Synthetic render failure with TEST-ID');}
function Shell({children,initial='/patients'}){return <MemoryRouter initialEntries={[initial]}><Controls/><main id="main-content" tabIndex={-1}><RouteExperience>{children || <Routes><Route path="/patients" element={<input aria-label="Patient search"/>}/><Route path="/patients/:id" element={<h1>Patient chart</h1>}/><Route path="/broken" element={<Failure/>}/><Route path="/" element={<h1>Home</h1>}/><Route path="/dashboard" element={<h1>Workspace</h1>}/></Routes>}</RouteExperience></main></MemoryRouter>;}
beforeEach(()=>{vi.spyOn(window,'scrollTo').mockImplementation(()=>{});auth.state={isAuthenticated:true,userInfo:{role:'patient'}};});
afterEach(()=>{vi.restoreAllMocks();});
test('page navigation updates a private title and moves focus to main',async()=>{
 render(<Shell/>);expect(document.title).toBe('病患 · AllCare365');fireEvent.click(screen.getByRole('link',{name:'Open chart'}));await screen.findByRole('heading',{name:'Patient chart'});expect(document.title).toBe('病患紀錄 · AllCare365');expect(document.title).not.toContain('73');expect(document.getElementById('main-content')).toHaveFocus();expect(window.scrollTo).toHaveBeenCalledWith({top:0,left:0,behavior:'instant'});
});
test('query changes preserve form focus and do not reset scroll',()=>{
 render(<Shell/>);const search=screen.getByRole('textbox',{name:'Patient search'});search.focus();fireEvent.click(screen.getByRole('button',{name:'Update query'}));expect(search).toHaveFocus();expect(window.scrollTo).not.toHaveBeenCalled();
});
test.each([true,false])('render failure recovery resets boundary for authenticated=%s',async isAuthenticated=>{
 auth.state={isAuthenticated,userInfo:isAuthenticated?{role:'patient'}:null};
 vi.spyOn(console,'error').mockImplementation(()=>{});render(<Shell/>);fireEvent.click(screen.getByRole('link',{name:'Open broken'}));await screen.findByRole('heading',{name:'頁面無法載入'});expect(screen.getByRole('button',{name:'重新載入頁面'})).toBeInTheDocument();expect(screen.queryByText(/Synthetic render failure/)).not.toBeInTheDocument();expect(screen.queryByText(/TEST-ID/)).not.toBeInTheDocument();fireEvent.click(screen.getByRole('link',{name:isAuthenticated?'回到工作空間 →':'回到首頁 →'}));await screen.findByRole('heading',{name:isAuthenticated?'Workspace':'Home'});expect(screen.queryByRole('alert')).not.toBeInTheDocument();
});
test('lazy navigation announces loading and focuses content only after it resolves',async()=>{
 let finish;const Slow=lazy(()=>new Promise(resolve=>{finish=resolve;}));render(<Shell><Routes><Route path="/patients" element={<h1>Initial</h1>}/><Route path="/slow" element={<Slow/>}/></Routes></Shell>);const link=screen.getByRole('link',{name:'Open slow'});link.focus();fireEvent.click(link);expect(screen.getByRole('status')).toHaveTextContent('正在載入頁面');expect(link).toHaveFocus();await act(async()=>finish({default:()=> <h1>Resolved</h1>}));await screen.findByRole('heading',{name:'Resolved'});expect(document.getElementById('main-content')).toHaveFocus();
});
test.each([true,false])('unknown route offers a recovery destination for authenticated=%s',isAuthenticated=>{
 auth.state={isAuthenticated,userInfo:isAuthenticated?{role:'patient'}:null};
 render(<Shell initial="/missing"><PageNotFound/></Shell>);expect(screen.getByRole('heading',{name:'找不到這個頁面',level:1})).toBeInTheDocument();expect(screen.getByRole('link',{name:isAuthenticated?'回到工作空間 →':'回到首頁 →'})).toHaveAttribute('href',isAuthenticated?'/dashboard':'/');expect(document.title).toBe('找不到頁面 · AllCare365');
});
test('restricted account gets a predictable overview destination',async()=>{
 render(<MemoryRouter><ProtectedRoute allowedRoles={['researcher']}><p>Restricted data</p></ProtectedRoute></MemoryRouter>);await screen.findByRole('heading',{name:'目前帳號無法開啟此頁',level:1});expect(screen.getByRole('link',{name:'回到總覽'})).toHaveAttribute('href','/dashboard');expect(screen.queryByText('Restricted data')).not.toBeInTheDocument();
});

test('disease network has its own page title',()=>{expect(routeTitle('/disease-network')).toBe('疾病網絡');});
