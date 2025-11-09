
import React from 'react';

const Footer: React.FC = () => {
  return (
    <footer className="bg-white border-t border-slate-200">
      <div className="container mx-auto py-6 px-4 text-center text-slate-500">
        <p>&copy; {new Date().getFullYear()} NDT Master. Все права защищены.</p>
        <div className="mt-2 space-x-4">
          <a href="#" className="hover:text-primary">Контакты</a>
          <span>&middot;</span>
          <a href="#" className="hover:text-primary">Поддержка</a>
          <span>&middot;</span>
          <a href="#" className="hover:text-primary">Политика конфиденциальности</a>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
