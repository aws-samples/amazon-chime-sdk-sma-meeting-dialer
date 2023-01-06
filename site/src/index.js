import React from 'react';
import ReactDOM from 'react-dom';
import './index.css';
import App from './App';
import { ThemeProvider } from 'styled-components';
import { lightTheme } from 'amazon-chime-sdk-component-library-react';

ReactDOM.render(
    <ThemeProvider theme={lightTheme}>
        <App />
    </ThemeProvider>,
    document.getElementById('root'),
);
