import React from 'react';
import { vi } from 'vitest';
import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import WorkspaceNavigation from './WorkspaceNavigation';
let width, queries;
const changeWidth=next=>{width=next;queries.forEach(query=>{query.matches=query.media.includes('min-width') && width>=1200;query.listeners.forEach(listener=>listener({matches:query.matches}));});};
const mount=()=>render(<MemoryRouter initialEntries={['/patients']}><WorkspaceNavigation userInfo={{username:'Synthetic researcher',role:'researcher'}} logout={vi.fn()}/><main id="main-content" tabIndex={-1}>Synthetic content</main></MemoryRouter>);
beforeEach(()=>{width=600;queries=[];vi.stubGlobal('matchMedia',vi.fn(media=>{const query={media,matches:media.includes('min-width') && width>=1200,listeners:new Set(),addEventListener:(_type,listener)=>query.listeners.add(listener),removeEventListener:(_type,listener)=>query.listeners.delete(listener)};queries.push(query);return query;}));});
afterEach(()=>vi.unstubAllGlobals());
test('drawer is named, has an explicit close action and restores trigger focus',async()=>{
 mount();const trigger=screen.getByRole('button',{name:'開啟導覽'});act(()=>trigger.focus());fireEvent.click(trigger);const drawer=await screen.findByRole('dialog',{name:'工作空間導覽'});expect(trigger).toHaveAttribute('aria-expanded','true');expect(drawer).toHaveAttribute('aria-modal','true');fireEvent.click(within(drawer).getByRole('button',{name:'關閉導覽'}));await waitFor(()=>expect(screen.queryByRole('dialog')).not.toBeInTheDocument());expect(trigger).toHaveAttribute('aria-expanded','false');expect(trigger).toHaveFocus();
});
test('selecting a drawer destination restores main focus after exit',async()=>{
 mount();fireEvent.click(screen.getByRole('button',{name:'開啟導覽'}));const drawer=await screen.findByRole('dialog',{name:'工作空間導覽'});fireEvent.click(within(drawer).getByRole('link',{name:'健檢紀錄'}));await waitFor(()=>expect(screen.queryByRole('dialog')).not.toBeInTheDocument());expect(document.getElementById('main-content')).toHaveFocus();
});
test('crossing the desktop boundary closes an open modal at exactly 1200px',async()=>{
 mount();fireEvent.click(screen.getByRole('button',{name:'開啟導覽'}));await screen.findByRole('dialog',{name:'工作空間導覽'});await act(async()=>changeWidth(1199.5));expect(screen.getByRole('dialog',{name:'工作空間導覽'})).toBeInTheDocument();await act(async()=>changeWidth(1200));await waitFor(()=>expect(screen.queryByRole('dialog')).not.toBeInTheDocument());expect(document.getElementById('main-content')).toHaveFocus();
});
test('Escape closes the drawer and restores its trigger',async()=>{
 mount();const trigger=screen.getByRole('button',{name:'開啟導覽'});fireEvent.click(trigger);const drawer=await screen.findByRole('dialog',{name:'工作空間導覽'});fireEvent.keyDown(drawer,{key:'Escape'});await waitFor(()=>expect(screen.queryByRole('dialog')).not.toBeInTheDocument());expect(trigger).toHaveFocus();
});
