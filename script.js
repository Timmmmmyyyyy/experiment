// Language config
const LANGUAGES = {
    en: {
        locale: 'en',
        decimalSep: '.',
        clear: 'AC',
        del: 'DEL',
        htmlLang: 'en',
    },
    ru: {
        locale: 'ru',
        decimalSep: ',',
        clear: 'ОЧ',
        del: 'УД',
        htmlLang: 'ru',
    }
};

let currentLang = 'en';

class Calculator {
    constructor(previousOperandElement, currentOperandElement) {
        this.previousOperandElement = previousOperandElement;
        this.currentOperandElement = currentOperandElement;
        this.clear();
    }

    clear() {
        this.currentOperand = '0';
        this.previousOperand = '';
        this.operation = undefined;
    }

    delete() {
        if (this.currentOperand === '0') return;
        this.currentOperand = this.currentOperand.toString().slice(0, -1);
        if (this.currentOperand === '') this.currentOperand = '0';
    }

    appendNumber(number) {
        if (number === '.' && this.currentOperand.includes('.')) return;
        if (this.currentOperand === '0' && number !== '.') {
            this.currentOperand = number.toString();
        } else {
            this.currentOperand = this.currentOperand.toString() + number.toString();
        }
    }

    chooseOperation(operation) {
        if (this.currentOperand === '') return;
        if (this.previousOperand !== '') {
            this.compute();
        }
        this.operation = operation;
        this.previousOperand = this.currentOperand;
        this.currentOperand = '';
    }

    compute() {
        let computation;
        const prev = parseFloat(this.previousOperand);
        const current = parseFloat(this.currentOperand);
        if (isNaN(prev) || isNaN(current)) return;
        switch (this.operation) {
            case '+':
                computation = prev + current;
                break;
            case '-':
                computation = prev - current;
                break;
            case '*':
                computation = prev * current;
                break;
            case '/':
                computation = prev / current;
                break;
            case '%':
                computation = prev % current;
                break;
            default:
                return;
        }
        this.currentOperand = computation;
        this.operation = undefined;
        this.previousOperand = '';
    }

    getDisplayNumber(number) {
        const lang = LANGUAGES[currentLang];
        const stringNumber = number.toString();
        const integerDigits = parseFloat(stringNumber.split('.')[0]);
        const decimalDigits = stringNumber.split('.')[1];
        let integerDisplay;
        if (isNaN(integerDigits)) {
            integerDisplay = '';
        } else {
            integerDisplay = integerDigits.toLocaleString(lang.locale, { maximumFractionDigits: 0 });
        }
        if (decimalDigits != null) {
            return `${integerDisplay}${lang.decimalSep}${decimalDigits}`;
        } else {
            return integerDisplay;
        }
    }

    updateDisplay() {
        this.currentOperandElement.innerText = this.getDisplayNumber(this.currentOperand);
        if (this.operation != null) {
            this.previousOperandElement.innerText =
                `${this.getDisplayNumber(this.previousOperand)} ${this.operation}`;
        } else {
            this.previousOperandElement.innerText = '';
        }
    }
}

const previousOperandElement = document.getElementById('previous-operand');
const currentOperandElement = document.getElementById('current-operand');

const calculator = new Calculator(previousOperandElement, currentOperandElement);

function appendNumber(number) {
    calculator.appendNumber(number);
    calculator.updateDisplay();
}

function appendDecimal() {
    calculator.appendNumber('.');
    calculator.updateDisplay();
}

function appendOperator(operator) {
    calculator.chooseOperation(operator);
    calculator.updateDisplay();
}

function calculate() {
    calculator.compute();
    calculator.updateDisplay();
}

function clearDisplay() {
    calculator.clear();
    calculator.updateDisplay();
}

function deleteLast() {
    calculator.delete();
    calculator.updateDisplay();
}

function setLanguage(lang) {
    currentLang = lang;
    const cfg = LANGUAGES[lang];

    // Update HTML lang attribute
    document.getElementById('html-root').lang = cfg.htmlLang;

    // Update button labels
    document.getElementById('btn-clear').textContent = cfg.clear;
    document.getElementById('btn-del').textContent = cfg.del;
    document.getElementById('btn-decimal').textContent = cfg.decimalSep;

    // Update lang toggle active state
    document.getElementById('btn-en').classList.toggle('active', lang === 'en');
    document.getElementById('btn-ru').classList.toggle('active', lang === 'ru');

    // Refresh display with new locale
    calculator.updateDisplay();
}

// Keyboard Support
document.addEventListener('keydown', e => {
    if ((e.key >= '0' && e.key <= '9')) appendNumber(e.key);
    if (e.key === '.' || e.key === ',') appendDecimal();
    if (e.key === '+' || e.key === '-' || e.key === '*' || e.key === '/' || e.key === '%') appendOperator(e.key);
    if (e.key === 'Enter' || e.key === '=') calculate();
    if (e.key === 'Backspace') deleteLast();
    if (e.key === 'Escape') clearDisplay();
});
