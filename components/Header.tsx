
import React from 'react';
import { Page } from '../types';

interface HeaderProps {
  navigate: (page: Page) => void;
  currentPage: Page;
}

const NavLink: React.FC<{
  page: Page;
  currentPage: Page;
  navigate: (page: Page) => void;
  children: React.ReactNode;
}> = ({ page, currentPage, navigate, children }) => {
  const isActive = currentPage === page;
  return (
    <button
      onClick={() => navigate(page)}
      className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${
        isActive
          ? 'bg-primary-700 text-white'
          : 'text-sky-100 hover:bg-primary-500 hover:text-white'
      }`}
    >
      {children}
    </button>
  );
};


const Header: React.FC<HeaderProps> = ({ navigate, currentPage }) => {
  return (
    <header className="bg-primary shadow-md">
      <nav className="container mx-auto px-4">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center">
            <div className="flex-shrink-0 text-white font-bold text-xl cursor-pointer" onClick={() => navigate(Page.Home)}>
              NDT Master
            </div>
            <div className="hidden md:block">
              <div className="ml-10 flex items-baseline space-x-4">
                <NavLink page={Page.Home} currentPage={currentPage} navigate={navigate}>Главная</NavLink>
                <NavLink page={Page.CreateTechCard} currentPage={currentPage} navigate={navigate}>Создать техкарту</NavLink>
                <NavLink page={Page.QualityAssessment} currentPage={currentPage} navigate={navigate}>Оценка качества</NavLink>
                <NavLink page={Page.Dashboard} currentPage={currentPage} navigate={navigate}>Личный кабинет</NavLink>
              </div>
            </div>
          </div>
          <div className="hidden md:block">
            <div className="ml-4 flex items-center md:ml-6">
              <span className="text-sky-200 text-sm mr-4">Вам доступно: 3 разработки</span>
              <div className="relative">
                <button className="max-w-xs bg-primary-700 rounded-full flex items-center text-sm focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-primary-800 focus:ring-white">
                  <span className="sr-only">Open user menu</span>
                  <img className="h-8 w-8 rounded-full" src="https://picsum.photos/32/32" alt="" />
                </button>
              </div>
            </div>
          </div>
        </div>
      </nav>
    </header>
  );
};

export default Header;
