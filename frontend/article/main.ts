import { mount } from 'svelte';
import Article from './Article.svelte';

const app = mount(Article, { target: document.getElementById('article')! });
export default app;
