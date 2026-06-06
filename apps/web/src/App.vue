<template>
  <q-layout view="hHh lpR fFf">
    <q-header elevated><q-toolbar><q-toolbar-title>Personal OS</q-toolbar-title></q-toolbar></q-header>
    <q-drawer show-if-above bordered>
      <q-list>
        <q-item to="/" clickable><q-item-section>Home</q-item-section></q-item>
        <q-item to="/study" clickable><q-item-section>Study</q-item-section></q-item>
        <q-item to="/zettelkasten" clickable><q-item-section>Zettelkasten</q-item-section></q-item>
        <q-item to="/geospatial" clickable><q-item-section>Geospatial</q-item-section></q-item>
        <q-item to="/sync" clickable><q-item-section>Sync Health</q-item-section></q-item>
      </q-list>
    </q-drawer>
    <q-page-container><router-view /></q-page-container>
  </q-layout>
</template>
